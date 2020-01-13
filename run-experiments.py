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
ev_res_glob = ResolEvaluator(gold_group='gns', tolerance_local=161)
ev_res_street = ResolEvaluator(gold_group='raw', tolerance_local=1)

pipe = builder.build('spacy')

gwn.bulk_process(pipe, saved_steps=[
                 'spacy', 'loc', 'gaz', 'geores', 'clust'], evaluator=ev_res_street)
