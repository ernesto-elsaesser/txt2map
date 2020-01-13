from annotation import *
from evaluation import *

spacy_url = 'http://localhost:8001'
cogcomp_url = 'http://localhost:8002'
builder = PipelineBuilder(spacy_url=spacy_url, cogcomp_url=cogcomp_url)

# corpora
tests = Corpus('Tests')
gwn = Corpus('GeoWebNews')
lgl = Corpus('LGL')

# evaluators
ev_rec = RecogEvaluator()
ev_rec_noclu = RecogEvaluator(include_clusters=False)
ev_rec_ner = RecogEvaluator(layer='ner', include_clusters=False)
ev_res = ResolEvaluator()
ev_res_noclu = ResolEvaluator(include_clusters=False)
ev_res_161 = ResolEvaluator(tolerance_local=161)
ev_res_street = ResolEvaluator(gold_group='raw', tolerance_local=1)
count = Counter('res', 'raw', count_gold=True)

pipe = builder.build_loc('spacy')
# imp_tests.import_documents(tests)
#tests.bulk_process(cc_full, evaluator=ev)

#tests.bulk_process(gcnl_gaz, evaluator=ev_rec)
#tests.bulk_process(gcnl, saved_steps=['tok', 'gcnl', 'loc', 'gaz'], evaluator=ev)
#tests.process(gcnl_gaz, 'global_demonyms_hard', saved_steps=['tok', 'gcnl'])

gwn.bulk_process(pipe, evaluator=ev_rec)
#gwn.bulk_process(spacy_nores, saved_steps=['spacy', 'loc', 'gaz'], evaluator=ev_rec)
#gwn.bulk_process(spacy_noclust, saved_steps=['spacy', 'loc', 'gaz', 'geores'], evaluator=ev_161)
#gwn.bulk_process(spacy, saved_steps=['spacy', 'loc', 'gaz', 'geores', 'clust'], evaluator=ev_161)

#gwn.bulk_process(cc_nogaz, saved_steps=['tok', 'cogcomp', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(cc_nores, saved_steps=['tok', 'cogcomp', 'loc', 'gaz'], evaluator=ev_rec)
#gwn.bulk_process(cc_noclust, saved_steps=['tok', 'cogcomp', 'loc', 'gaz', 'geores'], evaluator=ev_161)
#gwn.bulk_process(cc, saved_steps=['tok', 'cogcomp', 'loc', 'gaz', 'geores', 'clust'], evaluator=ev_161)

#gwn.bulk_process(gcnl_nogaz, evaluator=ev_rec)
#gwn.bulk_process(gcnl_nores, saved_steps=['tok', 'gcnl', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(gcnl_noclust, saved_steps=['tok', 'gcnl', 'loc', 'gaz'], evaluator=ev_161)
#gwn.bulk_process(gcnl, saved_steps=['tok', 'gcnl', 'loc', 'gaz', 'geores', 'clust'], evaluator=ev_161)

#gwn.process(gcnl_nogaz, '12')
