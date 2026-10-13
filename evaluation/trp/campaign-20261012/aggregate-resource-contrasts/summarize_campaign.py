#!/usr/bin/env python3
"""Summarize every prospective ID, without treating unknown or retries as new cases."""
import csv,hashlib,json,statistics,os
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cohort(inputs,outcomes,select_reviews=True):
 plan=load(inputs/'freeze.json');rows=[]
 for item in plan['cases']:
  local=outcomes/item['id'];p=local/'independent-audit.json'
  review=local/'review-resolution.json';descriptor_review=local/'review-fd.json'
  if p.is_file():
   selected=descriptor_review if select_reviews and descriptor_review.is_file()else(review if select_reviews and review.is_file()else p)
   interpretation='fatal-descriptor-review'if selected==descriptor_review else('causal-resolution-review'if selected==review else'frozen-original')
   r=load(selected);r.update({'auditSha256':sha(selected),'auditPath':str(selected.relative_to(HERE.parent.parent.parent.parent)),'firstAuditSha256':sha(p),'firstAuditPath':str(p.relative_to(HERE.parent.parent.parent.parent)),'selectedInterpretation':interpretation})
   if review.is_file():r.update({'resolutionReviewSha256':sha(review),'resolutionReviewPath':str(review.relative_to(HERE.parent.parent.parent.parent))})
   if descriptor_review.is_file():r.update({'fdReviewSha256':sha(descriptor_review),'fdReviewPath':str(descriptor_review.relative_to(HERE.parent.parent.parent.parent))})
  else:
   r={'case':item['id'],'physicalFeasibilityLabel':None,'actualDecision':None,'observationStatus':'not-observed','scientificR24Rate':None}
   if (local/'recovery.json').is_file():
    recovered=load(local/'recovery.json');r.update({'actualExitCode':recovered['actualExitCode'],'observationStatus':'recovered-awaiting-independent-audit','recoverySha256':sha(local/'recovery.json')})
  if (local/'dispatch-intent.json').is_file():r['dispatchIntentSha256']=sha(local/'dispatch-intent.json')
  if (local/'recovery.json').is_file():r['recoverySha256']=sha(local/'recovery.json')
  r['graphId']=item['graphId'];r['cohort']=item['cohort'];r['budgetWorkBytes']=item['budget']['workBytes'];rows.append(r)
 observed=[r for r in rows if 'actualExitCode'in r];labeled=[r for r in rows if r.get('physicalFeasibilityLabel')is not None and r.get('actualDecision')is not None]
 feasible=[r for r in labeled if r['physicalFeasibilityLabel']is True];infeasible=[r for r in labeled if r['physicalFeasibilityLabel']is False]
 falseRejected=[r for r in feasible if not r['actualDecision']['accepted']];falseAccepted=[r for r in infeasible if r['actualDecision']['accepted']]
 complete=[r for r in feasible if r.get('defaultPortableVerifier',{}).get('ok')]
 signed=[r['observedOverestimationFraction']for r in feasible if r.get('observedOverestimationFraction')is not None]
 excess=[r for r in observed if r.get('allocatedBlockBytesObservedPeak',0)>r['budgetWorkBytes']]
 decisions=[r for r in observed if r.get('actualDecision')is not None]
 boundExcess=[r for r in decisions if r['actualDecision']['accepted']and (r.get('observedUnderestimateBytes')or 0)>0]
 counts={'planned':len(rows),'observed':len(observed),'feasible':len(feasible),'infeasible':len(infeasible),'unknown':len(rows)-len(feasible)-len(infeasible),'notObserved':len(rows)-len(observed),'accepted':sum(r['actualDecision']['accepted']for r in labeled),'rejected':sum(not r['actualDecision']['accepted']for r in labeled),'correct':len(feasible)-len(falseRejected)+len(infeasible)-len(falseAccepted),'falseRejections':len(falseRejected),'falseAdmissions':len(falseAccepted),'actualBudgetExcessCases':len(excess),'admittedPredictionBoundExcessCases':len(boundExcess),'verifiedColdFullSuccesses':len(complete),'reproducibleCountCases':sum(any(c['name']=='actual-prospective-count-reproducibility'and c['ok']for c in r.get('checks',[]))for r in feasible),'attempts':len(observed)}
 rates={'classificationAccuracy':counts['correct']/len(labeled)if labeled else None,'falseRejectionRate':len(falseRejected)/len(feasible)if feasible else None,'falseAdmissionRate':len(falseAccepted)/len(infeasible)if infeasible else None,'medianSignedStorageOverestimation':statistics.median(signed)if signed else None,'medianPositiveOnlyStorageOverestimation':statistics.median(max(0,v)for v in signed)if signed else None,'falseRejectionThreshold':.05,'storageOverestimationThreshold':.25,'falseRejectionThresholdMet':len(falseRejected)/len(feasible)<=.05 if feasible else None,'storageMarginThresholdMet':statistics.median(max(0,v)for v in signed)<=.25 if signed else None,'scientificR24Rate':None}
 counts.update({'dispatched':sum('dispatchIntentSha256'in r for r in rows),'decisionObserved':len(decisions),'accepted':sum(r['actualDecision']['accepted']for r in decisions),'rejected':sum(not r['actualDecision']['accepted']for r in decisions),'unknownObserved':sum(r.get('physicalFeasibilityLabel')is None for r in observed),'attempts':sum('dispatchIntentSha256'in r for r in rows)})
 applicable=plan['mode']=='campaign';minimum=applicable and len(feasible)>=20 and len(infeasible)>=20
 return {'counts':counts,'rates':rates,'rows':rows,'freezeSha256':sha(inputs/'freeze.json'),'allPlannedObserved':len(observed)==len(rows),'actualMinima20EachApplicable':applicable,'actualMinima20EachMet':minimum if applicable else None,'allObservedLabeled':len(labeled)==len(observed),'oneDevelopmentProtein':True,'minimumInterpretation':'The minimum of twenty actual feasible and twenty actual infeasible applies only to the original forty contrasts. The six separately frozen boundary contrasts have no twenty-case minimum; the copied generic minimum metadata in that frozen file does not alter their planned denominator.'}

def main():
 original=cohort(HERE/'campaign-inputs',HERE/'campaign-outcomes');boundary=cohort(HERE/'boundary-inputs',HERE/'boundary-outcomes')
 supplement=cohort(HERE/'extension-inputs',HERE/'extension-outcomes')if(HERE/'extension-inputs/freeze.json').is_file()else None
 smokes=[]
 for p in sorted(HERE.glob('smoke-outcomes*/summary.json')):smokes.append({'path':str(p.relative_to(HERE)),'sha256':sha(p),'summary':load(p)})
 control=HERE/'copy-causal-controls/mechanism-review.json'
 frozen_original=cohort(HERE/'campaign-inputs',HERE/'campaign-outcomes',False);frozen_boundary=cohort(HERE/'boundary-inputs',HERE/'boundary-outcomes',False)
 result={'schema':'helix-aggregate-resource-original40-plus-boundary6/1.0','originalCounts':original['counts'],'originalRates':original['rates'],'boundaryCounts':boundary['counts'],'boundaryRates':boundary['rates'],'original':original,'boundary':boundary,'frozenOriginalAuditorCounts':frozen_original['counts'],'frozenBoundaryAuditorCounts':frozen_boundary['counts'],'auditorAmendmentPath':str((HERE/'auditor-amendment.json').relative_to(HERE.parent.parent.parent.parent)),'auditorAmendmentSha256':sha(HERE/'auditor-amendment.json'),'auditorSourceOverlayPath':str((HERE/'auditor-source-overlay.json').relative_to(HERE.parent.parent.parent.parent)),'auditorSourceOverlaySha256':sha(HERE/'auditor-source-overlay.json'),'historicalSmokes':smokes,'copyMechanismQualified':load(control)['mechanismQualified'],'copyMechanismReviewSha256':sha(control),'sourceProducerCommit':'ecfab67','sourceProducerStorageProfile':'trp-colocated-client-storage/1.0.0','scientificR24Rate':None,'uniqueProteins':1,'scope':'Engineering same-scope full Helix tool client/bootstrap/SQLite/cache/temp, co-located Python/Nextflow and worker NFS data plus actual portable export under one kernel quota and actual cgroups; preinstalled runtime/sharedDocker caches/root-only experiment telemetry excluded','all46Observed':original['allPlannedObserved']and boundary['allPlannedObserved'],'rawUnknownsPreserved':True,'summarySourceSha256':sha(Path(__file__))}
 if supplement is not None:
  result.update({'extension':supplement,'extensionCounts':supplement['counts'],'extensionRates':supplement['rates'],'extensionDesign':'Separate post-original-observation minimum-support cohort; its new graph IDs and budgets were frozen before its outputs. Original forty and boundary six remain separate.','allRequiredCloudCasesObserved':result['all46Observed']and supplement['allPlannedObserved']})
  def combined(groups):
   rows=[r for g in groups for r in g['rows']];counts={key:sum(g['counts'][key]for g in groups)for key in original['counts']};known=counts['feasible']+counts['infeasible'];signed=[r['observedOverestimationFraction']for r in rows if r.get('physicalFeasibilityLabel')is True and r.get('observedOverestimationFraction')is not None]
   rates={'classificationAccuracy':counts['correct']/known if known else None,'falseRejectionRate':counts['falseRejections']/counts['feasible']if counts['feasible']else None,'falseAdmissionRate':counts['falseAdmissions']/counts['infeasible']if counts['infeasible']else None,'medianSignedStorageOverestimation':statistics.median(signed)if signed else None,'scientificR24Rate':None}
   return {'counts':counts,'rates':rates,'minimaTwentyFeasibleTwentyInfeasibleMet':counts['feasible']>=20 and counts['infeasible']>=20,'oneDevelopmentProtein':True,'scientificPopulationEstimate':False}
  result['originalPlusSupplement']=combined([original,supplement]);result['allEngineeringIncludingBoundary']=combined([original,boundary,supplement]);result['minimumTechnicalSupportMet']=result['originalPlusSupplement']['minimaTwentyFeasibleTwentyInfeasibleMet']
 temporary=HERE/'summary.json.tmp';temporary.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');os.replace(temporary,HERE/'summary.json')
 with(HERE/'cases.csv').open('w')as f:
  names=['case','graphId','cohort','physicalFeasibilityLabel','budgetWorkBytes','predictedWorkBytes','allocatedBlockBytesObservedPeak','observedOverestimationFraction','actualExitCode','elapsedSeconds','observationStatus']
  writer=csv.DictWriter(f,fieldnames=['group',*names],extrasaction='ignore');writer.writeheader()
  groups=[('original40',original),('boundary6',boundary)]+([('minimumSupplement',supplement)]if supplement else[])
  for label,data in groups:
   for row in data['rows']:writer.writerow({'group':label,**row})
 print(json.dumps({'originalCounts':result['originalCounts'],'boundaryCounts':result['boundaryCounts'],'all46Observed':result['all46Observed']}))
if __name__=='__main__':main()
