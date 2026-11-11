import json, zipfile, pathlib, datetime
archive=pathlib.Path(__file__).with_name('supplier-risk-resilience-dss-week11-model-validation.zip')
with zipfile.ZipFile(archive) as z:
 def read(suffix):
  name=next(n for n in z.namelist() if n.endswith(suffix))
  return json.loads(z.read(name)),name
 test,testpath=read('/w10_2c_test_output/w10_2c_independent_test_report.json')
 selection,selpath=read('/evaluation/kpi23_validation_selection.json')
results={}
for k in ['kpi2_shortage','kpi3_emergency_premium']:
 r=test['results'][k]['overall']; model=r['selected_model']; baseline=r['zero_baseline']
 results[k]={'historical_test_mae':model['mae'],'zero_baseline_mae':baseline['mae'],'improvement_vs_zero_percent':round(100*(baseline['mae']-model['mae'])/baseline['mae'],2),'historical_test_rows':model['n']}
results['kpi3_emergency_premium']['historical_chained_comparator_mae']=test['results']['kpi3_emergency_premium']['overall']['chained_shortage_x_known_premium']['mae']
checks={'test_partition_not_used_for_selection':test['test_used_for_selection_or_tuning'] is False,'zero_po_overlap':test['po_overlap_across_all_partitions']==0,'week11_selection_uses_validation':selection['evaluation_partition']=='validation','week11_selection_reports_no_final_test_access':selection['final_test_accessed_in_week11'] is False,'revised_kpi2_monotonic_violations_zero_on_validation':selection['kpi2']['revised_monotonicity_violations']==0,'revised_kpi3_monotonic_violations_zero_on_validation':selection['kpi3']['revised_monotonicity_violations']==0,'historical_kpi2_better_than_zero_baseline':results['kpi2_shortage']['historical_test_mae']<results['kpi2_shortage']['zero_baseline_mae'],'historical_kpi3_better_than_zero_baseline':results['kpi3_emergency_premium']['historical_test_mae']<results['kpi3_emergency_premium']['zero_baseline_mae']}
report={'scope':'Independent audit of saved report numbers and selection provenance; NOT a new inference run or final independent test of revised Week 11 scoring','sources':[testpath,selpath],'historical_results':results,'validation_selection':{'kpi2_revised_mae':selection['kpi2']['revised_mae'],'kpi3_revised_mae':selection['kpi3']['revised_chained_monotonic_mae']},'checks':checks,'checks_passed':sum(checks.values()),'checks_total':len(checks),'critical_gap':'Week 11 revised cumulative-maximum KPI2 and chained corrected KPI3 must be scored on frozen held-out test data; historical direct-model test metrics do not establish revised-method held-out performance.','limitations':selection.get('limitations',[])}
out=pathlib.Path(__file__).with_name('Week12_KPI23_Evidence_Audit.json');out.write_text(json.dumps(report,indent=2));print(json.dumps({'passed':report['checks_passed'],'total':report['checks_total'],'results':results,'report':str(out)},indent=2))
