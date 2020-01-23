from geoparser import *
from evaluation import *

builder = PipelineBuilder()
builder.spacy_url = 'http://localhost:8001'
builder.cogcomp_url = 'http://localhost:8002'
builder.stanford_url = 'http://localhost:8003'

tr_pipe = TopoResolverClient('http://localhost:8004')

# corpora
tests = Corpus('Tests')
gwn = Corpus('GeoWebNews')
lgls = Corpus('LGL-Street')

# evaluators
ev_ner = NEREvaluator()
ev_ner_org = NEREvaluator(groups=['loc', 'org'])
ev_ner_org_per = NEREvaluator(groups=['loc', 'org', 'per'])
ev_rec = RecogEvaluator()
ev_res = ResolEvaluator()
ev_res_glob = ResolEvaluator(gold_group='geonames')
ev_res_street = ResolEvaluator(gold_group='raw')
ev_res_lgls = ResolEvaluator(measure_accuracy=False)
ev_res_gritta = ResolEvaluator(gold_group='geonames', geonames_by_dist=True) 

pipe = builder.build('spacy')

#imp = TestsImporter()
#imp.import_documents(tests)

tests.bulk_process(pipe, evaluator=ev_res)

# saved_steps=['spacy', 'gaz', 'geores', 'clust'], 
#lgls.process(pipe, '40647404')


