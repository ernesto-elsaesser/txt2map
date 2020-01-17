from annotation import *
from evaluation import *

from geoparser import GeoNamesCache, GeoNamesAPI

builder = PipelineBuilder()
builder.spacy_url = 'http://localhost:8001'
builder.cogcomp_url = 'http://localhost:8002'
builder.stanford_url = 'http://localhost:8003'
builder.topores_url = 'http://localhost:8004'

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
ev_res_glob = ResolEvaluator(gold_group='gns')
ev_res_street = ResolEvaluator(gold_group='raw')
ev_res_lgls = ResolEvaluator(gold_group='non', measure_accuracy=False)
ev_res_gritta = ResolEvaluator(gold_group='gns', gns_by_dist=True) 

pipe = builder.build('spacy')

#imp = GeoWebNewsImporter()
#imp.import_documents(gwn)

#gwn.bulk_process(pipe, saved_steps=['stanford', 'gaz', 'geores'], evaluator=ev_res_street)

#lgls.bulk_process(pipe, saved_steps=['stanford', 'gaz', 'geores'], evaluator=ev_res_lgls)
# saved_steps=['spacy', 'gaz', 'geores', 'clust'], 
gwn.process(pipe, '289')

