#!/usr/bin/env python3
"""Operator allocation and guard for a genuine co-located Helix/Slurm client.

Guest-only commands require root and an explicit owner-prepared profile. This
script never starts/stops AWS instances, changes previous R24 allocations, or
installs a checker implicitly. Client configuration has no SSH/API credentials.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import socket
import subprocess
import time
import uuid

VERSION = "trp-remote-strict/1.0.0"
POLICIES = Path("/run/helix-remote-strict")
CHECKER = Path("/usr/local/libexec/helix-remote-strict-check.py")
MOUNT = Path("/shared/helix-strict")
STORE = Path("/srv/helix-strict-store")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+".tmp")
    descriptor = os.open(temporary, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, mode)
    with os.fdopen(descriptor,"w") as file:
        json.dump(value,file,sort_keys=True,allow_nan=False)
        file.write("\n")
    temporary.chmod(mode)
    temporary.replace(path)


def run(argv, **kwargs):
    return subprocess.run(argv,text=True,capture_output=True,**kwargs)


def require_root():
    if os.geteuid()!=0:raise ValueError("Owner guest provisioning requires root")


def readonly_checker():
    for path in [CHECKER.parent,CHECKER]:
        info=path.lstat()
        if info.st_uid!=0 or info.st_mode&0o022 or path.is_symlink():
            raise ValueError("Checker must already be installed root-owned and immutable to client")
    return sha(CHECKER)


def filesystem():
    data=json.loads(run(["findmnt","--json","--mountpoint",str(MOUNT),"--output","TARGET,SOURCE,FSTYPE,OPTIONS,UUID"],check=True).stdout)["filesystems"]
    if len(data)!=1 or data[0]["fstype"]!="xfs" or not {"prjquota","pquota"}.intersection(data[0]["options"].split(",")):
        raise ValueError("Exact XFS project-quota mount required")
    return data[0]


def init_mount(output):
    require_root()
    if STORE.exists() or MOUNT.exists():raise ValueError("Existing allocation/image must be preserved; use a distinct revision")
    STORE.mkdir(mode=0o700);MOUNT.mkdir(mode=0o711)
    image=STORE/"disk.img"
    descriptor=os.open(image,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    os.ftruncate(descriptor,2*1024**3);os.close(descriptor)
    mkfs=run(["mkfs.xfs","-f",str(image)],check=True)
    mounted=run(["mount","-o","loop,prjquota,allocsize=4k",str(image),str(MOUNT)],check=True)
    identity=filesystem()
    report={"schema":"helix-strict-operator-filesystem/1.0","createdAtUtc":datetime.now(timezone.utc).isoformat(),
            "image":str(image),"imageBytes":image.stat().st_size,"mount":identity,
            "newFilesystemOnly":True,"previousR24Touched":False,"mkfsStdout":mkfs.stdout,"mountStdout":mounted.stdout}
    write(output,report)
    return report


def allocate(work_bytes,project,expiry,user,output):
    require_root()
    if work_bytes<=0 or work_bytes%4096 or project<=0:raise ValueError("Positive4KiB-aligned quota and unique project required")
    mounted=filesystem();checker_sha=readonly_checker();account=pwd.getpwnam(user)
    for pointer in POLICIES.glob("hrs*.json"):
        if pointer.name.endswith(".sample.json"):continue
        existing=json.loads(pointer.read_text())
        if existing.get("filesystem",{}).get("projectId")==project:raise ValueError("Project ID already appears in an immutable policy; preserve orphan and choose a fresh namespace")
    if account.pw_uid<=0:raise ValueError("Client must not be quota-exempt root")
    identifier="hrs"+uuid.uuid4().hex[:16]
    POLICIES.mkdir(mode=0o755,exist_ok=True)
    if POLICIES.stat().st_uid!=0 or POLICIES.stat().st_mode&0o022:raise ValueError("Root policy directory ownership differs")
    allocation=MOUNT/identifier
    allocation.mkdir(mode=0o711);os.chown(allocation,account.pw_uid,account.pw_gid)
    paths={"allocationRoot":str(allocation),"clientWorkspace":str(allocation/"client"),
           "temporaryRoot":str(allocation/"tmp"),"exportRoot":str(allocation/"export"),
           "clientStateRoot":str(allocation/"state"),"clientCacheRoot":str(allocation/"cache"),"remoteRoot":str(allocation/"remote")}
    for value in list(paths.values())[1:]:
        path=Path(value);path.mkdir(mode=0o711);os.chown(path,account.pw_uid,account.pw_gid)
    group_name="helix-strict-"+identifier+".service"
    group=Path("/sys/fs/cgroup")/group_name
    group.mkdir(mode=0o755)
    for name,value in {"cpu.max":"100000 100000","memory.max":"2147483648","memory.swap.max":"0","memory.oom.group":"1"}.items():
        (group/name).write_text(value)
    target={"host":"127.0.0.1","port":22,"user":user,"hostKeyAlias":"helix-colocated",
            "root":paths["remoteRoot"],"partition":"helix","selectNode":"helix-worker1",
            "geometryNode":"helix-worker2","numericalProfile":"haswell-single-thread"}
    policy={"version":VERSION,"id":identifier,"uid":account.pw_uid,"hostname":socket.gethostname(),
            "bootId":Path("/proc/sys/kernel/random/boot_id").read_text().strip(),"target":target,
            "filesystem":{"mountPoint":str(MOUNT),"uuid":mounted["uuid"],"device":allocation.stat().st_dev,
                          "projectId":project,"hardBytes":work_bytes},"paths":paths,
            "controller":{"cgroup":group_name,"cpus":1,"memoryBytes":2147483648,"swapBytes":0},
            "entitlement":{"cpus":3,"memoryBytes":4294967296,"workBytes":work_bytes,"wallSeconds":1080},
            "checker":{"path":str(CHECKER),"sha256":checker_sha},"samplePath":str(POLICIES/(identifier+".sample.json"))}
    pointer=POLICIES/(identifier+".json");write(pointer,policy)
    config={"version":"trp-slurm-ssh/1.0.0",**target,"strictPolicy":str(pointer),"sessionExpiresAt":expiry}
    config_path=allocation/"client"/"remote.json";write(config_path,config,0o600);os.chown(config_path,account.pw_uid,account.pw_gid)
    # Only operator metadata is created before assignment/enforcement. Its actual
    # blocks are charged to this same project, then verified before client code.
    run(["xfs_quota","-x","-c",f"project -s -p {allocation} {project}",str(MOUNT)],check=True)
    run(["xfs_quota","-x","-c",f"limit -p bhard={work_bytes//1024}k {project}",str(MOUNT)],check=True)
    charged=quota_sample(policy,sha(pointer))
    if charged["quota"]["usedBytes"]>work_bytes:raise ValueError("Initial charged operator metadata exceeds the actual kernel budget")
    report={"schema":"helix-strict-operator-allocation/1.0","createdAtUtc":datetime.now(timezone.utc).isoformat(),
            "policyPath":str(pointer),"policySha256":sha(pointer),"policy":policy,"configPath":str(config_path),
            "configSha256":sha(config_path),"helperSha256":sha(Path(__file__)),
            "operatorMetadataCreatedBeforeQuota":True,"operatorMetadataChargedAndVerifiedBeforeClient":charged,"clientInputOrPreparationBeforeQuota":False,
            "cgroupCreation":"Direct root-controlled cgroup v2 leaf, not a systemd unit","credentialsCopied":False}
    write(output,report)
    return report


def quota_sample(policy,policy_sha):
    fs=policy["filesystem"];paths=policy["paths"]
    report=run(["xfs_quota","-x","-c","report -p -b -n",fs["mountPoint"]],check=True).stdout
    found=re.findall(r"^#"+str(fs["projectId"])+r"\s+(\d+)\s+(\d+)\s+(\d+)\s",report,re.M)
    if len(found)!=1:raise ValueError("Project quota missing/ambiguous")
    used,soft,hard=map(int,found[0]);state=run(["xfs_quota","-x","-c","state -p",fs["mountPoint"]],check=True).stdout
    tree=run(["xfs_quota","-x","-c",f"project -c -p {paths['allocationRoot']} {fs['projectId']}",fs["mountPoint"]])
    if hard*1024!=fs["hardBytes"] or "Accounting: ON"not in state or "Enforcement: ON"not in state:
        raise ValueError("Actual quota enforcement differs from immutable policy")
    # This xfsprogs version emits two informational lines even when no inode
    # fails. Preserve its raw stdout and expose only diagnosed inode failures
    # to the immutable checker. Any unexpected text remains a refusal.
    expected=[f"Checking project {fs['projectId']} (path {paths['allocationRoot']})...",
              f"Processed 1 (/etc/projects and cmdline) paths for project {fs['projectId']} with recursion depth infinite (-1)."]
    diagnostics=tree.stdout
    if tree.stdout.splitlines()==expected:diagnostics=""
    sample={"version":"trp-remote-strict-sample/1.0.0","policySha256":policy_sha,"observedAt":time.time(),
            "bootId":policy["bootId"],"quota":{"projectId":fs["projectId"],"usedBytes":used*1024,"hardBytes":hard*1024,
            "reportSource":report,"stateSource":state,"treeCheckExitCode":tree.returncode,
            "treeCheckStdout":diagnostics,"treeCheckRawStdout":tree.stdout,"treeCheckStdoutIsDiagnostics":True,"treeCheckStderr":tree.stderr}}
    write(Path(policy["samplePath"]),sample)
    return sample


def owned_jobs(comments):
    rows=run(["squeue","--noheader","--format=%i|%k"],check=True).stdout.splitlines()
    return [row.split("|",1)[0]for row in rows if "|"in row and row.split("|",1)[1]in comments]


def terminate_group(group,comments):
    if (group/"cgroup.kill").is_file():(group/"cgroup.kill").write_text("1")
    jobs=owned_jobs(comments)
    if jobs:run(["scancel",*jobs],check=True)
    end=time.monotonic()+20
    while owned_jobs(comments)and time.monotonic()<end:time.sleep(.25)
    return {"requested":jobs,"remaining":owned_jobs(comments)}


def supervise(allocation_path,argv,deadline,output):
    require_root()
    if not argv:raise ValueError("Explicit actual client argv required")
    allocation=json.loads(allocation_path.read_text());policy=allocation["policy"]
    pointer=Path(allocation["policyPath"])
    if sha(pointer)!=allocation["policySha256"] or sha(CHECKER)!=policy["checker"]["sha256"]:
        raise ValueError("Policy/checker changed before client launch")
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    group=Path("/sys/fs/cgroup")/policy["controller"]["cgroup"]
    account=pwd.getpwuid(policy["uid"]);paths=policy["paths"]
    env={"PATH":os.environ.get("PATH","/usr/local/bin:/usr/bin:/bin"),"LANG":"C.UTF-8","USER":account.pw_name,
         "TMPDIR":paths["temporaryRoot"],"XDG_STATE_HOME":paths["clientStateRoot"],"XDG_CACHE_HOME":paths["clientCacheRoot"],
         "XDG_DATA_HOME":paths["clientStateRoot"]+"/data","XDG_CONFIG_HOME":paths["clientStateRoot"]+"/config",
         "BUN_INSTALL_CACHE_DIR":paths["clientCacheRoot"]+"/bun","BUN_RUNTIME_TRANSPILER_CACHE_PATH":paths["clientCacheRoot"]+"/transpiler",
         "PYTHONPYCACHEPREFIX":paths["clientCacheRoot"]+"/python","HELIX_TEST_HOME":paths["clientStateRoot"]+"/home",
         "HELIX_TEST_MANAGED_CONFIG_DIR":paths["clientStateRoot"]+"/managed","HELIX_TRP_REMOTE":allocation["configPath"],
         "NXF_OFFLINE":"true","NXF_DISABLE_CHECK_LATEST":"true","HELIX_DISABLE_MODELS_FETCH":"true",
         "NXF_TEMP":paths["temporaryRoot"],"NXF_OPTS":"-Djava.io.tmpdir="+paths["temporaryRoot"]}
    for name in ["NXF_HOME","HELIX_MODELS_PATH","HELIX_TRP_PYTHON"]:
        if os.environ.get(name):env[name]=os.environ[name]
    def child_setup():
        os.setsid();(group/"cgroup.procs").write_text("0")
        os.initgroups(account.pw_name,account.pw_gid);os.setgid(account.pw_gid);os.setuid(account.pw_uid)
    initial=quota_sample(policy,allocation["policySha256"])
    global_stat=os.statvfs(MOUNT)
    global_health={"path":str(MOUNT),"device":MOUNT.stat().st_dev,"globalFreeBytes":global_stat.f_bavail*global_stat.f_frsize,"globalFreeInodes":global_stat.f_favail,"observedAt":time.time(),"scope":"Unassigned XFS mount root, not quota-clipped client path"}
    comments=set();samples=[];started=time.monotonic();cause=None
    # Pipes carry only experiment telemetry outside the allocation. Client
    # production logs/state and its requested portable export stay inside it.
    process=subprocess.Popen(argv,cwd=paths["clientWorkspace"],env=env,preexec_fn=child_setup,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=False)
    os.set_blocking(process.stdout.fileno(),False);os.set_blocking(process.stderr.fileno(),False)
    buffers={"stdout":bytearray(),"stderr":bytearray()};partial=""
    try:
        while True:
            sample=quota_sample(policy,allocation["policySha256"])
            cg={name:(group/name).read_text().strip()for name in ["cpu.max","memory.max","memory.swap.max","memory.current","memory.peak","memory.events","cgroup.events"]}
            samples.append({"elapsedSeconds":time.monotonic()-started,"quota":sample,"cgroup":cg})
            for name,pipe in [("stdout",process.stdout),("stderr",process.stderr)]:
                try:chunk=os.read(pipe.fileno(),65536)
                except BlockingIOError:chunk=b""
                if chunk:
                    buffers[name].extend(chunk)
                    if name=="stdout":
                        partial+=chunk.decode(errors="replace")
                        while "\n"in partial:
                            line,partial=partial.split("\n",1)
                            if line.startswith("HELIX_OWNED_UUID:"):
                                value=line.split(":",1)[1].strip()
                                if not re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}",value):raise ValueError("Untrusted owner comment identifier")
                                comments.add("helix:"+value)
            events=dict(line.split()for line in cg["memory.events"].splitlines())
            if int(events.get("oom_kill",0))>0:cause="actual-controller-cgroup-oom";break
            if time.time()>=deadline:cause="actual-global-checkpoint";break
            if time.monotonic()-started>policy["entitlement"]["wallSeconds"]:cause="actual-approved-wall-watchdog";break
            if process.poll()is not None:break
            time.sleep(.5)
    finally:
        cleanup=terminate_group(group,comments)
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        for name,pipe in [("stdout",process.stdout),("stderr",process.stderr)]:
            try:
                while True:
                    chunk=os.read(pipe.fileno(),65536)
                    if not chunk:break
                    buffers[name].extend(chunk)
            except BlockingIOError:pass
        for value in re.findall(rb"(?m)^HELIX_OWNED_UUID:([0-9a-f-]{36})\s*$", bytes(buffers["stdout"])):
            text=value.decode()
            if re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}",text):comments.add("helix:"+text)
        # A final drained UUID is still cancelled before claiming quiescence.
        cleanup=terminate_group(group,comments)
        end=time.monotonic()+5
        while "populated 1" in (group/"cgroup.events").read_text() and time.monotonic()<end:time.sleep(.1)
        final_cgroup={name:(group/name).read_text().strip()for name in ["cgroup.events","cgroup.procs","memory.events","memory.peak","cpu.max","memory.max","memory.swap.max"]}
        final=quota_sample(policy,allocation["policySha256"])
        for name,data in buffers.items():(output/("experiment-telemetry."+name)).write_bytes(data)
        report={"schema":"helix-full-client-root-supervision/1.0","policySha256":allocation["policySha256"],
                "clientArgv":argv,"publicChildEnvironment":env,"actualExitCode":process.returncode,"terminationCause":cause,
                "ownedComments":sorted(comments),"nativeCleanup":cleanup,"samples":samples,"finalCgroup":final_cgroup,
                "controllerAndTracerReaped":process.returncode is not None and final_cgroup["cgroup.procs"]=="" and "populated 0"in final_cgroup["cgroup.events"],
                "initialQuota":initial,"initialGlobalFilesystemHealth":global_health,"finalQuota":final,"elapsedSeconds":time.monotonic()-started,
                "scope":"Actual client preparation/state/cache/tmp/export and head run in one XFS project; actual client and head controller share a1CPU/2GiB cgroup; workers2CPU/2GiB each sequentially.",
                "privateCredentialsCopied":False,"helperSha256":sha(Path(__file__))}
        write(output/"supervision.json",report)
        # Retain the real allocation after terminal cancellation and before any
        # operator transport/cleanup. This copy is study archive after measuring.
        shutil.copytree(paths["allocationRoot"],output/"retained-allocation",symlinks=True)
        write(output/"export-ready.json",{"supervisionSha256":sha(output/"supervision.json"),"sourceTerminal":True})
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="action",required=True)
    init=sub.add_parser("guest-init");init.add_argument("--output",type=Path,required=True)
    create=sub.add_parser("guest-allocation");create.add_argument("--work-bytes",type=int,required=True);create.add_argument("--project",type=int,required=True);create.add_argument("--expiry",required=True);create.add_argument("--user",default="ubuntu");create.add_argument("--output",type=Path,required=True)
    start=sub.add_parser("guest-supervise");start.add_argument("--allocation",type=Path,required=True);start.add_argument("--deadline",type=float,required=True);start.add_argument("--output",type=Path,required=True);start.add_argument("client_argv",nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.action=="guest-init":result=init_mount(a.output)
    elif a.action=="guest-allocation":result=allocate(a.work_bytes,a.project,a.expiry,a.user,a.output)
    else:result=supervise(a.allocation,[v for v in a.client_argv if v!="--"],a.deadline,a.output)
    print(json.dumps({"action":a.action,"ok":True,"policySha256":result.get("policySha256"),"exitCode":result.get("actualExitCode")}))


if __name__=="__main__":main()
