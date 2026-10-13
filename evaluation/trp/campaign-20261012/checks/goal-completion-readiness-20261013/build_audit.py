#!/usr/bin/env python3
"""Read-only, timestamped goal readiness snapshot; writes this review directory only."""
from pathlib import Path
import collections, hashlib, json, subprocess
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[5]
CAMP=ROOT/'evaluation/trp/campaign-20261012'
OUT=Path(__file__).resolve().parent
GOAL=Path('/home/webiwabou/.codex/attachments/6fb1e6f3-caa6-490f-bf80-bd1ed8726787/pasted-text-1.txt')
sha=lambda x:hashlib.sha256(x).hexdigest()
sources={}
def read(p):
 p=Path(p);p=p if p.is_absolute() else ROOT/p
 raw=p.read_bytes();name=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
 sources[name]={'sha256':sha(raw),'bytes':len(raw)}
 return json.loads(raw)
def ref(n):return 'evaluation/trp/campaign-20261012/'+n

goalraw=GOAL.read_bytes();sources[str(GOAL)]={'sha256':sha(goalraw),'bytes':len(goalraw),'fullTextRead':True}
plan=read(CAMP/'campaign-plan.json');protocol=read(ROOT/'evaluation/trp/protocol.json');trace=read(ROOT/'docs/tesis/trazabilidad.json')
ids=[x['id'] for x in protocol['metrics']];assert ids==[x['id'] for x in trace['resultados']] and len(ids)==21
work=read(CAMP/'cloud/workflow-summary.json');first=[x for x in work['attempts'] if not x.get('retry',False)]
# Attempt labels in the captured schema are explicit.
first=[x for x in work['attempts'] if x.get('attempt_kind')=='first'] if any('attempt_kind' in x for x in work['attempts']) else first
print('ATTEMPTschema',list(work['attempts'][0]))
static=read(CAMP/'checks/contract-graphs.json'); mapping=read(CAMP/'mapping-public-contrasts/summary.json');negative=read(CAMP/'event-negative-contrasts/audit.json')
read(CAMP/'trace/event-negative-second-review.json')
struct=read(CAMP/'structural/summary.json');sasa=read(CAMP/'structural/freesasa/summary.json');long=read(CAMP/'structural/runtime-600/summary.json')
model=read(CAMP/'model-pilot/audit.json');settings=read(CAMP/'model-pilot/settings-probe-request/audit.json')
head=read(CAMP/'cloud/lab2/r24-campaign/all-original-attempts.json')
strictbase=CAMP/'aggregate-resource-contrasts';freeze=read(strictbase/'campaign-inputs/freeze.json');boundary=read(strictbase/'boundary-inputs/freeze.json')
assert len(freeze['cases'])==40 and len(boundary['cases'])==6
frozen_sources=[]
for name,expected in freeze['sourceHashes'].items():
 p=ROOT/name;raw=p.read_bytes();actual=sha(raw);sources[name]={'sha256':actual,'bytes':len(raw)};frozen_sources.append({'path':name,'expected':expected,'actual':actual,'matches':actual==expected})
read(strictbase/'auditor-amendment.json')
if (strictbase/'auditor-source-overlay.json').exists():read(strictbase/'auditor-source-overlay.json')
original=read(strictbase/'campaign-outcomes/summary.json')
post=[]
for n in ['review-resolution-summary.json','review-fd-summary.json']:
 p=strictbase/'campaign-outcomes'/n
 if p.exists():post.append({'path':str(p.relative_to(ROOT)),'summary':read(p)})
known={x['case'] for x in original['rows']};pending=[x['id'] for x in freeze['cases'] if x['id'] not in known]
strictproof=read(CAMP/'checks/strict-full-client-final-offline/attempt-2/audit.json');faults=read(CAMP/'checks/strict-full-client-final-offline/attempt-2/fault-injection.json');patchtests=read(CAMP/'checks/strict-full-client-final-offline/staged-hardening/test-results.json')
assert strictproof['verified'] and faults['detected']==460 and faults['semanticDetected']==19 and patchtests['successful']
doc=read(CAMP/'document/checks.json');render=read(CAMP/'document/rendered-intermediate-audit.json')
scan=read(CAMP/'checks/versioning-content-review-20261013/verification.json')
read(CAMP/'checks/versioning-content-review-20261013/git-delivery-analysis.json')
read(CAMP/'cloud/lab1/stop-state.json');read(CAMP/'cloud/lab2/r24-stop-state.json')
# Observe current renewals from captured records only; no portal/SSH/API operations.
renew=[]
for p in (CAMP/'cloud/lab2').glob('*renew*/*.json'):
 try:renew.append({'path':str(p.relative_to(ROOT)),'value':read(p)})
 except (ValueError,TypeError):pass
new=read(CAMP/'cloud/lab2/budget-observation-20261013.json')

technical_evidence={
 'R1.1':['packages/helix/src/trp/catalog.json'],
 'R1.2':[ref('model-pilot/audit.json'),ref('checks/strict-full-client-final-offline/attempt-2/audit.json')],
 'R1.3':['docs/tesis/evaluacion-experta-20260930/para-asesora/evaluacion.xlsx'],
 'R1.4':['evaluation/trp/protocol.json',ref('campaign-plan.json'),ref('aggregate-resource-contrasts/campaign-inputs/freeze.json')],
 'R1.5':[ref('cloud/workflow-summary.json'),ref('checks/strict-full-client-final-offline/attempt-2/audit.json')],
 'R1.6':[ref('mapping-public-contrasts/summary.json'),ref('trace/mapped-reference.json')],
 'R1.7':[ref('checks/contract-graphs.json'),ref('cloud/workflow-summary.json')],
 'R1.8':[ref('cloud/workflow-summary.json'),ref('trace/running-cancellation-clean.json')],
 'R1.9':[ref('checks/contract-graphs.json'),ref('contract-corpus/freeze.json')],
 'R2.1':[ref('checks/strict-full-client-final-offline/attempt-2/audit.json'),ref('aggregate-resource-contrasts/campaign-outcomes/summary.json')],
 'R2.2':[ref('aggregate-resource-contrasts/calibration-before-final-campaign.json'),ref('aggregate-resource-contrasts/campaign-outcomes/summary.json')],
 'R2.3':[ref('event-negative-contrasts/audit.json'),ref('aggregate-resource-contrasts/campaign-outcomes/summary.json')],
 'R2.4':[ref('cloud/lab2/r24-campaign/all-original-attempts.json'),ref('aggregate-resource-contrasts/campaign-inputs/freeze.json'),ref('aggregate-resource-contrasts/campaign-outcomes/summary.json')],
 'R3.1':[ref('checks/strict-full-client-final-offline/attempt-2/fault-injection.json'),ref('trace/mapped-reference.json')],
 'R3.2':[ref('event-negative-contrasts/audit.json'),ref('trace/event-negative-second-review.json'),ref('checks/strict-full-client-final-offline/attempt-2/audit.json')],
 'R3.3':['docs/tesis/evaluacion-experta-20260930/para-asesora/evaluacion.xlsx'],
 'R3.4':[ref('checks/strict-full-client-final-offline/attempt-2/audit.json'),ref('checks/strict-full-client-final-offline/staged-hardening/test-results.json')],
 'R3.5':['packages/helix/src/trp/structural_catalog.json',ref('structural/summary.json')],
 'R3.6':[ref('structural/summary.json'),ref('structural/runtime-600/summary.json'),ref('structural/freesasa/summary.json')],
 'R3.7':[ref('structural/freesasa/integration/agent-reference.json'),ref('structural/summary.json')],
 'R3.8':[ref('structural/summary.json'),ref('structural/freesasa/summary.json')],
}
# A status here concerns the requirement and current scope, not the UI label implemented.
status={
 'R1.1':('verified_for3admitted_of6audited','Full documentation/reference coverage is assessed only on admitted entries. ReUPred runtime and RepeatsDB contract expansion remain outside the currently admitted composition scope. No claim full universe support.'),
 'R1.2':('implemented_and_development_verified','Four real model pilots and digest-bound executable specifications; independent language correctness is R1.3, not established by supplied development facts.'),
 'R1.3':('external_human_reference_pending','70 real requests, expert selected; definitive references/feasibility and two paraphrases per feasible intention have not been delivered. Scientific three-replicate rates are null.'),
 'R1.4':('21definitions_and_amendments_available','Main40, boundary6, developer calibration and later observer corrections are separately dated; final scientific freeze requires independent partitions.'),
 'R1.5':('technical50variants_verified_scientific_pending','52 attempts,48 first successes,2 retained first failures,2 repaired retries,50 unique final verifications on one development protein. Independent50-intent execution denominator is unavailable.'),
 'R1.6':('mapping_development_verified_bounded_domains','30public chains,11751label-author correspondences,30SIFTS parsers,28prepared/11215residues,2correct missing-CA rejects; twelve-unit remote mapped reference. No observed insertion/alternate domain or biological annotation claim.'),
 'R1.7':('supported_route_static_and_stub_verified','50static positives,30static negatives and actual stub/real traversals. Reserved independent reference corpus remains unavailable.'),
 'R1.8':('technical_reports_verified','Explicit failed/omitted/not-evaluable states and causes retained; physical classifier coverage is not implied.'),
 'R1.9':('30development_invalids_checked_independent_reserve_pending','Development0/30invalid acceptance with30expected reasons and no validator exceptions, separate from independent T-GRAPH.'),
 'R2.1':('dated_hashed_target_inventory_verified_current_campaign_pending','Actual controller/worker witnesses and strict receipts are observed; final run-by-run inventory/window coverage awaits main campaign terminal audit.'),
 'R2.2':('strict_same_scope_implemented_pilot_and_onecase_verified_aggregate_pending','Ordinary12MiB and calibrated strict32MiB profiles stay distinct. Full client/controller/staging/export is now actually accounted in one project; no final campaign medians/count/overrun claim before complete terminal audit.'),
 'R2.3':('typed_resource_rejections_verified_final_counts_pending','Ordinary requests without required hard scope are refused. Counterfactual executor bypasses only workBytes rejection, retains real decisions, and never changes root quota/caps.'),
 'R2.4':('original_head_metric_failed_new_same_scope_campaign_active','Original40head:26feasible14infeasible6false rejects=23.08%,34/40accuracy85%, fails5%threshold; posthoc6separate. New strict40+boundary6 not yet complete. Scientific diverse TRP resource metric is not established.'),
 'R3.1':('strict150all_artifact_faults_verified_engineering','Original anchors detect460/460faults; semantic19/19 with additional observer, restored green. Standard verifier strict semantic hardening is staged and must be applied/audited after live campaign terminal.'),
 'R3.2':('negative13actions_verified_strict10mandatorypath_verified','Four negative sessions match13prospectively expected live callback/guard records with source/cause/order; synthetic actors. Strict success has10source-backed mandatory gates but no separately captured success callback action oracle. No universal human-session coverage.'),
 'R3.3':('external_human_turn_labels_pending','At least100actual turns, first independent non-adjudicated labels, coverage/confusion/paired task correctness and kappa remain unavailable; synthetic approvals do not substitute.'),
 'R3.4':('strict24source_fields_and_prose_verified_staged_default_hardening','Independent observer verifies24/24mandatory field pointers/values and exact strict prose. Frozen generic verifier accepts3of19semantic defects; staged candidate closes those and actual approval channel/answer defects while6external baseline bundles remain valid.'),
 'R3.5':('nine_mechanical_modes_documented_physical_mode_unvalidated','C9 has optional CCTBX/FreeSASA descriptive observables; broad fold verdict remains not_evaluable. No new biological cutoff or classifier.'),
 'R3.6':('mechanical_and_descriptive_controls_verified_physical_rules_pending','CCTBX105/108 at180s;3retained timeouts recovered in separate600s contrast. FreeSASA108/108, including missing atoms/uncharged residues; coverage is observable availability rather than physical failure detection.'),
 'R3.7':('per_instance_provenance_verified_bounded_scope','OriginalPratt78 supplied coordinate/PAE sets, per-instance frame/version/scales/values and optional wrapper digest/export. Timeouts and secondary profile remain separate; external source is not automatically redistributable.'),
 'R3.8':('external_physical_rule_and_applicable_negative_labels_pending','78originals available,30reviewed experimental repeats do not certify absence of physical failure. No validated classifier/cutoff, specificity or sensitivity. Require external physical adjudication and suitable controls, not extra clouds.'),
}
rows=[]
for met in protocol['metrics']:
 i=met['id'];row=next(x for x in trace['resultados'] if x['id']==i);state,note=status[i]
 rows.append({'id':i,'title':row['titulo'],'exactProtocolMeasurement':met['measurement'],'exactProtocolAcceptance':met['acceptance'],'currentEvidenceState':state,'interpretation':note,'evidence':technical_evidence[i],'scientificFinalMetricClaimed':False})

requirements=[
 ('U01','Execute all currently viable pending tests, update implementation/report','active','Strict40/boundary6 plus final observer/render/lifecycle still viable and required; no reliance on human pending to stop technical work.'),
 ('U02','Use authorized repository/Word/context, exclude credentials','verified_bounded','Original Word still preserved; existing private configs used by owners; actual new credential/content scan is separately underway.'),
 ('U03','Audit21current IDs, done/pending/dependencies, reuse valid evidence','verified_current_snapshot','Exact21IDs match current protocol/trace. Historical attempts, calibrations and unknowns retained.'),
 ('U04','Complete remote automatic transfer/resource/approval/submit/track/retrieve/cancel/errors/provenance','implemented_actual_engineering_verified','Real SSH two-lab50variant campaign, cleanrunning cancellation, mapping and strictcohost real client. Positive approvals synthetic; actual scheduler312terminal gap requires diagnostic, not fabricated status.'),
 ('U05','Execute planned tests with available data/model/annotations/resources incl failure/recovery','active','Source-independent negative13 sessions, nativefailure/cancel, exactGolds, physicsobservables and publicnumberings completed; strictmatrix completion and finalcold audit remain.'),
 ('U06','Analyze and update report, annexes, traceability, reproduction','active','Protected chapters1–3 preserved in candidate; original not installed. Newstrict fault/method proof and reproducible recipe available; final matrix/results still to integrate.'),
 ('U07','Two Academy accounts independent; no pooling','verified_actual_setup','Two3nodeclusters used for independent engineering campaigns. Strict3CPU/4GiB entitlement is controller plus one sequential worker, not workerRAM pooling.'),
 ('U08','Observe credits/permissions/capacity/time before campaign','verified_captured_records_final_refresh_required','Academy metadata read-only works and native/guest receipts constrain freshwindows. USD49.2latestUI remaining has reportingdelay and is not a final bill.'),
 ('U09','Manage4h sessions/180mboot guards/checkpoints','verified_active','Officialrenewal restarts VMs; per-node boot minimum must be refreshed. Original freeze global checkpoint06:49; later owner checkpoint must preserve progress and not alter thresholds.'),
 ('U10','Copy evidence periodically, stop idle compute, accountstorage','active','Most campaigns recovered locally; latestLab2renewal invalidates oldfinalstop claim. Finalownedjobs/controllerquiescence and stoppedEC2/EBSinventory still required.'),
 ('U11','ExtraUSD50accounts only demonstratedcreditneed','no_current_evidence_of_shortage','Credits are not pooled; account size/IAM restrictions persist. No request needed from delayed portal balance currently available.'),
 ('U12','Adapt prospectively, preservequestion/thresholds/failures','verified_with_explicit_limitations','Originalhead-only matrix failed retained. Strictrealclient scope and32MiBcalibration frozen beforeprimary; separatelysixnear-boundaries. Laterobservercausal corrections are post-observation and cannot be called prospective.'),
 ('U13','Use agreed model/limits and recordwhatactuallyobserved','development_verified_limit_absence_disclosed','gpt-6-sol/mediumOAuth fourpilots, correctedAPI-equivalent.1200792USD, actualbill/revision/tierunexposed. Requested8192outputtokens not hardenforced; operationalguards are distinct.'),
 ('U14','No invented labels/kappa/sensitivity/specificity','verified_current_bounded_evidence','Everyheldoutscientific metric remainsnull unless actualreferencevalid. Strictfeasibility labels are resource engineering, not physicalbiology.'),
 ('U15','Keep external annotation pending; continue independenttasks','verified_active','Expert selected70request workbook no answers; strictcloud/observer/Word technicalwork continues without those labels.'),
 ('U16','Separate engineering/exploration/scientific; Pratt not allcontrols','verified_explicit','78 originals available; CCTBX/FreeSASA describe108cases but C9broadnot_evaluable and physicalspecificitynull.'),
 ('U17','Coordinated agents/protectuserchanges/Helixbranding/Englishcommits','coordinated_root_final_commit_pending','Own writes onlynewcheckdirectories/tmp; AWS,Word,cannonical andcommit ownership remainsroot.'),
 ('U18','No emdash in new Word; red pendingnotes','root_final_word_gate_pending','Read-only review doesnoteditWord. Finalrootcandidate/rendercheck must include currentmetrics withouttouching350protectedbodyelements.'),
 ('U19','Deliver reproducible tests/traces/resultsummary; stopinfra; do notcallthesiscomplete','active_not_complete','Newrecipe uses supportedCLI,newoutput/coldcopy, scopes/gold/freeze. Finaldelivery/stop and externalvalidations remainopen.'),
]
req=[{'id':i,'requirement':r,'status':s,'evidenceInterpretation':n} for i,r,s,n in requirements]
viable=[
 {'priority':1,'id':'strict-main40-and-boundary6-terminal','owner':'root/evaluation_audit','action':'Finish/resume prospectively frozen cases, recover originals before any repair, retain primary and post-observation causal reviews separately. Resolve unknowns honestly or execute separately frozen extensions if minima need support. Never reuse failed outcomes as successes or label scheduler failure budget-infeasible.','evidenceCurrent':{'expectedMainCases':40,'observedMainCases':original['actualObservedCases'],'pendingMainIds':pending,'primaryActualFeasible':original['actualFeasible'],'primaryActualInfeasible':original['actualInfeasible'],'primaryUnknown':original['unknown'],'boundaryPlanned':6,'boundaryObserved':len(list((strictbase/'boundary-outcomes').glob('BOUND-*'))) if (strictbase/'boundary-outcomes').exists() else 0}},
 {'priority':1,'id':'strict-default-verifier-semantic-hardening','owner':'root_after_all_live_terminal','action':'Apply staged verifier-only patch afterallcampaigns terminal, retain oldfrozenbytes/commit. Verify new3semanticgaps and approval channel/answer, backwardscompatible ordinary12MiB/mapped/cancel/negative. No rerunscience. Record amendment, not retroactiveproducerhashreplacement.','stagedTests':{'tests':patchtests['tests'],'cases':len(patchtests['cases']),'successful':patchtests['successful'],'originalSha256':patchtests['originalSha256'],'candidateSha256':patchtests['candidateSha256'],'patchSha256':patchtests['patchSha256']}},
 {'priority':1,'id':'native-stub-timeout-diagnosis','owner':'root/evaluation_audit','action':'AGG13generous stubs: SELECT311completed, GEOMETRY312submitted/PENDING then lost from retained active+trace witness. Nextflow480s watchdogfailed beforeScience; absent.begin/log/exitcode. InspectownerSlurm/workerlogs and preserve unknown. InvalidAccount is also transientin successfulcontrols so insufficient asrootcause. No quota/OOMcause demonstrated.'},
 {'priority':2,'id':'source-backed-final-word-annex-canon','owner':'root','action':'Integrate finalstrictmatrix, originalfailedhead40, semanticfix/amendments, ownproofs, human/physics pending, scopes/denominators into results/conclusions/annex/trace. Finalcoldsourcehashaudit, renderpagechecks andinstalloriginalWord only afterprotectedchaptersverify.'},
 {'priority':2,'id':'final-archive-secret-delivery-delta-scan','owner':'root/scientific_controls','action':'Finalfreshscan afternewbundles/Word/copiedreview outputs; includearchivesandSQLite innercontainers and privateoriginalequality scope. Decide metadata/codevsrecoveredarchivesdelivery and reproduceexternal dependency/archivehashes. Do not claim oldsnapshotcoversnewoutputs.'},
 {'priority':2,'id':'fresh-final-both-lab-lifecycle','owner':'root','action':'Afterlocalcopies, confirmallownedjobs/controllers/workercontainersquiet, stopunusedinstances usingownerSDK, retainfreshstop/storageinventory. Lab2old03:52stop was supersededbyofficial03:59renewal, not current finalstate.'},
 {'priority':3,'id':'final-review-and-title-only-commits','owner':'root','action':'Source/protocol21IDs/candidatehash/CLIreproduction checks; English-title commitswithoutcoauthor. Finalsummaryexactverified/partial/dependency. Goalmayfinishviablework, thesisnotcomplete whilehuman/physicsmetricsmissing.'},
]
external=[{'results':['R1.3','R1.5'],'requires':'Expert definitiveexpectedflows, facts/feasibility, twoindependentparaphrases and reservedfreeze/actualevaluation; workbook fields currentlyempty.'},{'results':['R3.3'],'requires':'Actual sessions/≥100turns, blindnon-adjudicatedindependentlabels andpairedtaskcorrectness, thenCohenκ/confusion. Drivercallbackssyntheticarenothuman labels.'},{'results':['R3.8'],'requires':'Externalphysicaldecisionrule andapplicablephysicalpositive/negativeadjudication. Thirtyreviewedrepeatstructures arenotcertifiedphysicalnegativecontrols; originalPrattalone cannotestablishspecificity.'}]
counts=work['counts'];assert counts['attempts']==len(work['attempts'])==52
first=[a for a in work['attempts'] if a['revision_directory']=='workflows']
repaired=[a for a in work['attempts'] if a['revision_directory']=='workflows-repaired']
assert len(first)==50 and len(repaired)==2
assert sum(a['status']=='succeeded' for a in first)==48 and sum(a['status']=='failed' for a in first)==2
assert sum(a['status']=='succeeded' for a in repaired)==2
assert len({a['id'] for a in work['attempts'] if a['verified']})==50
linked_attempts=[]
for a in work['attempts']:
    verified=[]
    for key,hashkey in [('case_path','case_sha256'),('audit_path','audit_sha256')]:
        if key not in a:
            verified.append({'field':key,'available':False,'reason':'Failed original attempt has no independent success audit; retained as failure, not a verified run'})
            continue
        path=Path(a[key]);path=path if path.is_absolute() else ROOT/path
        value=read(path)
        actual=sources[str(path.relative_to(ROOT))]['sha256']
        assert actual==a[hashkey], (a['id'],key)
        verified.append({'path':str(path.relative_to(ROOT)), 'sha256':actual})
    linked_attempts.append({'id':a['id'],'revisionDirectory':a['revision_directory'],'status':a['status'],'verified':a['verified'],'sourceLinks':verified})
for evidence in technical_evidence.values():
    for name in evidence:
        path=ROOT/name
        assert path.exists(), name
        if name.endswith('.json'):read(path)
        elif name not in sources:sources[name]={'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size}
actualstatuses=collections.Counter(a['status'] for a in work['attempts'])
scalars=lambda d:{k:v for k,v in d.items() if isinstance(v,(str,int,float,bool,type(None)))}
report={
 'schema':'helix-goal-completion-readiness/1.0','reviewedAtUtc':datetime.now(timezone.utc).isoformat(),'authorRole':'Independent technical reviewer of producer outputs; ownofflineobserver authored by sameagent, no human-rater independence claimed','readOnlyOriginals':True,'cloudOperations':0,'goalComplete':False,'thesisComplete':False,'all21ImplementationComplete':False,
 'goalRequirements':req,'milestones':[{'id':m['id'],'planStatusHistorical':m['status'],'currentAuditStatus':{'M1':'21currentIDs_and_baselineverified','M2':'actualsupportedSSH_andstrictcohostintegrationverified_bounded','M3':'50variants30invalids_negative13andstrictallartifactproofverified','M4':'same_scope_strict40boundary6_active_and_unknown_nativefailure','M5':'fouractualdevelopmentpilots_capsabsence_disclosed','M6':'humanexternalinputsnotreceived','M7':'descriptivephysicsverified_classifiernotvalidated','M8':'finalWord_delivery_lifecycle_pending'}[m['id']]} for m in plan['milestones']],
 'expectedResults':rows,'viableRequiredRemaining':viable,'externalIndependentDependencies':external,
 'closedTechnicalGaps':{'strictFullClientActuallyInsideQuotaAndCgroup':True,'newStrictArtifactFaultCoverage':faults['detected']==faults['injected']==460,'strictSemanticCasesWithObserver':faults['semanticDetected']==faults['semanticInjected']==19,'sourceBackedStrictMethodsFields':24,'strictSourceBackedMandatoryGates':10,'negativeIndependentActionsMatched':13,'negativeHumanActors':0,'defaultVerifierHardeningAppliedToProduction':False},
 'freshSourceFreezeComparison':{'checked':len(frozen_sources),'allMatchAtRead':all(x['matches'] for x in frozen_sources),'rows':frozen_sources,'observerOverlay':'Temporary observer change acknowledged and frozen auditor restored. Post-observation resolution/fd audits separately preserved; producer/thresholds/outcomes not rewritten.'},
 'observations':{'workflows':{'rawAttemptCount':len(work['attempts']),'counts':counts,'rawFirstCount':len(first),'rawRepairedCount':len(repaired),'linkedAttempts':linked_attempts,'rawStatusCounts':dict(actualstatuses),'rawAttemptSchema':list(work['attempts'][0]),'scientificR15':None},'mapping':scalars(mapping),'negativeActions':negative['eligible_records_by_source'],'CCTBXprimary':struct['groups'],'CCTBX600secondary':scalars(long),'FreeSASA':sasa['groups'],'model':{'completedCases':4,'model':model['requested_model'],'reasoning':model['configured_reasoning_effort'],'publishedAPIEquivalentUSD':model['published_standard_api_equivalent_usd'],'actualBilling':None,'hard8192Cap':settings['hard_provider_output_cap_enforced'],'sourceScope':model['scope']},'headOriginal40':scalars(head),'strictPrimaryProvisional':scalars(original),'strictPostObservationReviewsProvisional':[{'path':x['path'],'summary':scalars(x['summary'])} for x in post],'Word':{'generatedAt':doc['generated_at'],'originalOverwritten':doc['original_word_overwritten'],'sourceSha256':doc['source_sha256'],'protectedChaptersPreserved':doc['chapters_1_to_3_xml_preserved'],'protectedElements':doc['protected_body_elements'],'sourceEntries':len(doc['source_evidence']),'renderedIntermediateNotFinal':True},'currentScan':{'latestSnapshot':scan['latestSnapshot'],'finalRepeatRequired':scan['finalRepeatRequired']}},
 'optionalProductExtensionsNotGoalBlockers':['BroadenunadmittedReUPred/RepeatsDBcataloguecontracts','GPU/MPI/newarchitecture/performanceadvantage','Universalphysicalfoldclassifier orarbitrarymultihosthardquota withoutrootoperatorprofile','OAuth8192servercapnotdemonstrated; mandatoryiffuturefreezeclaimsahardbound, no inventedclaiminthisdevelopmentpilot'],
 'automaticIntegrationScope':'ProductionHelix toolservices andactualpersistentSQLite prepare/run, digestapproval, rechecks, nativeSlurm, retrieve/export/cancel/errors now exercised. OrdinarySSH andstrictcohost scopes separate. Syntheticapprovals/prebuiltdevelopmentfactsandwork-onlycounterfactualexecutorare disclosed; no claimfullnatural-languageagentautonomy or scientificcorrectness.',
 'reproductionFiles':['strict-reproduction.md','final-checks.md'],'sources':sources,
}
(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'path':str(OUT/'audit.json'),'expectedResults':len(rows),'goalRequirements':len(req),'currentMainObserved':original['actualObservedCases'],'currentMainPending':len(pending),'sourceFreezeAllMatch':report['freshSourceFreezeComparison']['allMatchAtRead'],'auditSha256':sha((OUT/'audit.json').read_bytes())},indent=2))
