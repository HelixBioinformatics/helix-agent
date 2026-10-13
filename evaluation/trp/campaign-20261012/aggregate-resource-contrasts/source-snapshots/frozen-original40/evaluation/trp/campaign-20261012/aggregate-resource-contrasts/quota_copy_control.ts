/** Independent bounded contrast of the exact Bun copyfile primitive. No jobs. */
import fs from 'node:fs/promises'
import crypto from 'node:crypto'
const [source,destination]=process.argv.slice(2)
const hash=(bytes:Uint8Array)=>crypto.createHash('sha256').update(bytes).digest('hex')
const input=await fs.readFile(source)
console.log('HELIX_COPY_CONTROL:'+JSON.stringify({pid:process.pid,atEpochSeconds:Date.now()/1000,source,destination,inputBytes:input.length,sourceSha256:hash(input),operation:'node:fs/promises.copyFile',fullWorkflowOracle:false}))
try{
 await fs.copyFile(source,destination)
 const out=await fs.readFile(destination)
 console.log('HELIX_COPY_CONTROL_RESULT:'+JSON.stringify({pid:process.pid,atEpochSeconds:Date.now()/1000,status:'succeeded',bytes:out.length,sha256:hash(out),equalsSource:out.equals(input),fullWorkflowOracle:false}))
}catch(error:any){
 console.log('HELIX_COPY_CONTROL_THROW:'+JSON.stringify({pid:process.pid,atEpochSeconds:Date.now()/1000,status:'failed',name:error.name,code:error.code,errno:error.errno,syscall:error.syscall,path:error.path,dest:error.dest,message:error.message,fullWorkflowOracle:false}));throw error
}
