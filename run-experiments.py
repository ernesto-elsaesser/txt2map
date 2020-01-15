from annotation import *
from evaluation import *

builder = PipelineBuilder()
builder.spacy_url = 'http://localhost:8001'
builder.cogcomp_url = 'http://localhost:8002'
builder.topores_url = 'http://localhost:8003'
builder.reocgnize_fac_ents = True

# corpora
tests = Corpus('Tests')
gwn = Corpus('GeoWebNews')
lgls = Corpus('LGL-Street')

# evaluators
ev_ner = NEREvaluator()
ev_rec = RecogEvaluator()
ev_res = ResolEvaluator()
ev_res_glob = ResolEvaluator(gold_group='gns')
ev_res_street = ResolEvaluator(gold_group='raw')
eval_wiki = WikiResolEvaluator()
eval_wiki_glob = WikiResolEvaluator(gold_group='gns')
eval_wiki_street = WikiResolEvaluator(gold_group='raw')

pipe = builder.build('spacy')
gwn.bulk_process(pipe, saved_steps=['spacy'], evaluator=ev_rec)
#tests.process(pipe, 'global_d_c')
