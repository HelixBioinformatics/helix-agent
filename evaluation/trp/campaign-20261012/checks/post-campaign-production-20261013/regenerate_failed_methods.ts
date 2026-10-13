await import("/home/webiwabou/Projects/bioinformatica-org/packages/core/src/global");
await import("/home/webiwabou/Projects/bioinformatica-org/packages/core/src/fs-util");
const {TrpEvidence}=await import("/home/webiwabou/Projects/bioinformatica-org/packages/helix/src/trp/evidence");
await TrpEvidence.methods(process.argv[2]);
