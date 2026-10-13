#!/usr/bin/env python3
"""Preserve and verify exact files in private external delivery archives.

The scientific action consumes an explicit source allowlist. The campaign action
requires a parent EOF receipt and stores all archive records outside the campaign.
No source file, Git state, provider state or cloud resource is modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import time
from datetime import datetime, timezone

ROOT = Path("/home/webiwabou/Projects/bioinformatica-org")
CAMPAIGN = ROOT / "evaluation/trp/campaign-20261012"


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2).encode() + b"\n"


def private_write(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def member_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\x00" in name:
        raise ValueError("Unsafe archive member path")
    return path


def source_record(path, member, expected=None, roles=None):
    member_path(member)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Source allowlist must contain regular files: " + str(path))
    sha = digest(path)
    after = path.lstat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Source changed during hash: " + str(path))
    if expected and (sha != expected["sha256"] or before.st_size != expected["bytes"]):
        raise ValueError("Source differs from existing manifest: " + str(path))
    return {"originalPath": str(path), "archiveMember": member, "bytes": before.st_size,
            "sha256": sha, "mtimeNs": before.st_mtime_ns, "roles": roles or []}


def scientific_records(plan):
    records = []
    source = json.loads(plan.read_text())
    allowed_pratt = ROOT / "evaluation/trp/reference/pratt-author-20261001"
    allowed_controls = Path.home() / ".local/state/helix/structural-20261012/controls"
    for row in source["files"]:
        path = Path(row["originalPath"])
        if not (path.is_relative_to(allowed_pratt) or path.is_relative_to(allowed_controls)):
            raise ValueError("Scientific source outside explicit dataset allowlist")
        records.append(source_record(path, row["archiveMember"], row, row["roles"]))
    if len(records) != 299 or len({r["archiveMember"] for r in records}) != 299:
        raise ValueError("Scientific source count/member uniqueness differs")
    return records, {"sourcePlanSha256": digest(plan), "sourcePlan": str(plan),
                     "payloadCounts": source["payloadCounts"], "controlInputs": 60,
                     "originalPathsAreFrozen": True,
                     "relocation": "Archive-member mapping preserves bytes. Frozen cohort CLIs require original declared paths; score-one supports explicit relocated input and new output."}


def campaign_records(receipt):
    authority = json.loads(receipt.read_text())
    if authority.get("campaignReadyForArchive") is not True:
        raise ValueError("Parent EOF receipt must confirm campaignReadyForArchive")
    if authority.get("campaignPath") != str(CAMPAIGN.relative_to(ROOT)):
        raise ValueError("EOF receipt scope differs")
    paths = sorted(CAMPAIGN.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("Unexpected outer campaign symlink; preserve and review it before packaging")
    records = [source_record(p, str(p.relative_to(ROOT))) for p in paths if p.is_file()]
    nonregular = [p for p in paths if not p.is_file() and not p.is_dir()]
    if nonregular:
        raise ValueError("Nonregular outer campaign entry requires explicit preservation review")
    directories = [str(CAMPAIGN.relative_to(ROOT))] + [str(p.relative_to(ROOT)) for p in paths if p.is_dir()]
    return records, {"eofReceiptSha256": digest(receipt), "eofReceipt": authority,
                     "campaignPrefix": str(CAMPAIGN.relative_to(ROOT)),
                     "directories": directories,
                     "archiveExclusions": [], "outerCampaignSymlinks": 0,
                     "scope": "All observed regular campaign files, including raw archives, extracted data, caches, failed cases and original interpretations. Nested archive bytes remain unchanged."}


def verify_source_set(records, action, directories):
    for row in records:
        path = Path(row["originalPath"])
        info = path.lstat()
        if info.st_size != row["bytes"] or info.st_mtime_ns != row["mtimeNs"] or digest(path) != row["sha256"]:
            raise ValueError("Preserved source changed: " + str(path))
    if action == "campaign":
        actual = {str(p.relative_to(ROOT)) for p in CAMPAIGN.rglob("*") if p.is_file()}
        if actual != {r["archiveMember"] for r in records}:
            raise ValueError("Campaign file set changed after EOF")
        actual_dirs = {str(CAMPAIGN.relative_to(ROOT))} | {str(p.relative_to(ROOT)) for p in CAMPAIGN.rglob("*") if p.is_dir()}
        if actual_dirs != set(directories):
            raise ValueError("Campaign directory set changed after EOF")


def make_archive(path, records, directories, metadata_raw, metadata_member):
    output = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    stderr = path.with_suffix(path.suffix + ".compression.stderr")
    err_fd = os.open(stderr, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(output, "wb") as compressed, os.fdopen(err_fd, "wb") as errors:
        process = subprocess.Popen(["zstd", "-q", "-T2", "-6", "--stdout"], stdin=subprocess.PIPE,
                                   stdout=compressed, stderr=errors)
        try:
            with tarfile.open(fileobj=process.stdin, mode="w|", format=tarfile.PAX_FORMAT, dereference=True) as archive:
                for directory in directories:
                    info = tarfile.TarInfo(directory)
                    info.type, info.mode = tarfile.DIRTYPE, 0o700
                    archive.addfile(info)
                for row in records:
                    info = archive.gettarinfo(row["originalPath"], arcname=row["archiveMember"])
                    if not info.isfile() or info.size != row["bytes"]:
                        raise ValueError("Archive source type/size changed")
                    info.mode = 0o600
                    with open(row["originalPath"], "rb") as source:
                        archive.addfile(info, source)
                import io
                info = tarfile.TarInfo(metadata_member)
                info.size, info.mode = len(metadata_raw), 0o600
                archive.addfile(info, io.BytesIO(metadata_raw))
            process.stdin.close()
            code = process.wait(timeout=900)
            if code:
                raise RuntimeError("zstd compression failed, exit " + str(code))
            compressed.flush()
            os.fsync(compressed.fileno())
        except BaseException:
            process.kill()
            process.wait()
            raise


def verify_archive(path, records, directories, metadata_raw, metadata_member, restored):
    expected = {row["archiveMember"]: row for row in records}
    restored.mkdir(mode=0o700)
    seen = set()
    seen_dirs = set()
    process = subprocess.Popen(["zstd", "-q", "-d", "--stdout", str(path)], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for info in archive:
                name = str(member_path(info.name))
                if info.isdir():
                    if name in seen_dirs or name not in directories:
                        raise ValueError("Unexpected or duplicate directory member")
                    seen_dirs.add(name)
                    restored.joinpath(*member_path(name).parts).mkdir(parents=True, exist_ok=True, mode=0o700)
                    continue
                if name in seen or not info.isfile() or (name not in expected and name != metadata_member):
                    raise ValueError("Unexpected, duplicate or nonregular archive member")
                seen.add(name)
                target = restored.joinpath(*member_path(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                value = hashlib.sha256()
                size = 0
                with os.fdopen(fd, "wb") as destination, archive.extractfile(info) as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        destination.write(chunk)
                        value.update(chunk)
                        size += len(chunk)
                if name == metadata_member:
                    if target.read_bytes() != metadata_raw:
                        raise ValueError("Embedded manifest differs from external manifest")
                elif size != expected[name]["bytes"] or value.hexdigest() != expected[name]["sha256"]:
                    raise ValueError("Restored bytes differ: " + name)
        process.stdout.close()
        code = process.wait(timeout=900)
        if code:
            raise RuntimeError("zstd decompression failed, exit " + str(code))
        if seen != set(expected) | {metadata_member}:
            raise ValueError("Archive membership incomplete")
        if seen_dirs != set(directories):
            raise ValueError("Archive directory membership incomplete")
        # pathlib's parents=True creates intermediate directories with the
        # process umask rather than the supplied leaf mode. Restrict every
        # newly extracted directory, leaving all source paths untouched.
        for directory in restored.rglob("*"):
            if directory.is_dir():
                directory.chmod(0o700)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    return {"payloadFiles": len(expected), "archiveRegularMembers": len(seen),
            "archiveDirectoryMembers": len(seen_dirs),
            "payloadBytes": sum(row["bytes"] for row in records),
            "allPayloadHashesMatchSources": True, "metadataByteIdentical": True,
            "freshRestoreDirectory": str(restored), "existingFilesOverwritten": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scientific", "campaign"])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--eof-receipt", type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Private archives must be outside the repository")
    if output.exists():
        raise ValueError("Refusing an existing delivery directory")
    if args.action == "scientific" and not args.plan:
        raise ValueError("Scientific action requires an explicit allowlist plan")
    if args.action == "campaign" and not args.eof_receipt:
        raise ValueError("Campaign action requires an explicit parent EOF receipt")
    output.mkdir(parents=True, mode=0o700)
    start = time.monotonic()
    print(json.dumps({"phase": "hashing-explicit-sources", "at": utc(), "action": args.action}), flush=True)
    records, binding = scientific_records(args.plan) if args.action == "scientific" else campaign_records(args.eof_receipt)
    metadata = {"schema": "helix-private-delivery-members/1.0", "createdAtUtc": utc(),
                "kind": args.action, "sourceRoot": str(ROOT), "privateLocalDelivery": True,
                "publicReleaseAuthorized": False, "binding": binding, "files": records,
                "fileCount": len(records), "fileBytes": sum(r["bytes"] for r in records),
                "sourceCodeSha256": digest(Path(__file__)), "credentialsOrExternalAppStateIncluded": False}
    raw = canon(metadata)
    metadata_path = output / "members.json"
    private_write(metadata_path, raw)
    metadata_member = "helix-delivery/" + args.action + "-members.json"
    archive = output / ("helix-20261012-" + args.action + ".tar.zst")
    print(json.dumps({"phase": "compressing", "sources": len(records), "bytes": metadata["fileBytes"]}), flush=True)
    directories = binding.get("directories", [])
    make_archive(archive, records, directories, raw, metadata_member)
    anchor = digest(archive)
    private_write(output / "archive.sha256", (anchor + "  " + archive.name + "\n").encode())
    print(json.dumps({"phase": "fresh-extraction-byte-verification", "archiveBytes": archive.stat().st_size}), flush=True)
    check = verify_archive(archive, records, directories, raw, metadata_member, output / "verified-restoration")
    verify_source_set(records, args.action, directories)
    if digest(archive) != anchor:
        raise ValueError("Archive changed during verification")
    receipt = {"schema": "helix-private-delivery-byte-verification/1.0", "verifiedAtUtc": utc(),
               "action": args.action, "archivePath": str(archive), "archiveSha256": anchor,
               "archiveBytes": archive.stat().st_size, "archiveMode": oct(stat.S_IMODE(archive.stat().st_mode)),
               "externalMembersManifest": str(metadata_path), "externalMembersSha256": digest(metadata_path),
               "verification": check, "sourceOriginalsUnchanged": True, "allSourceInputsVerifiedAfterPacking": True,
               "gitMutated": False, "awsCalls": 0, "credentialsCopied": False, "privateLocalDelivery": True,
               "publicReleaseAuthorized": False, "elapsedSeconds": time.monotonic() - start}
    private_write(output / "verification.json", canon(receipt))
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
