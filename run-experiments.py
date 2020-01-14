from annotation import *
from evaluation import *

builder = PipelineBuilder()
builder.spacy_url = 'http://localhost:8001'
builder.cogcomp_url = 'http://localhost:8002'
builder.topores_url = 'http://localhost:8003'

# corpora
tests = Corpus('Tests')
gwn = Corpus('GeoWebNews')
lgls = Corpus('LGL-Street')

# evaluators
ev_rec = RecogEvaluator()
ev_rec_noclu = RecogEvaluator(include_clusters=False)
ev_rec_ner = RecogEvaluator(layer='ner', include_clusters=False)
ev_res = ResolEvaluator()
ev_res_noclu = ResolEvaluator(include_clusters=False)
ev_res_161 = ResolEvaluator(tolerance_local=161)
ev_res_glob = ResolEvaluator(gold_group='gns', tolerance_local=161)
ev_res_street = ResolEvaluator(gold_group='raw', tolerance_local=161)

pipe = builder.build_empty()

print(len(lgls.document_ids()))

#gwn.bulk_process(pipe, saved_steps=['topores'], evaluator=ev_res_street)
