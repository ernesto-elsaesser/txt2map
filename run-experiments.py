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

pipe_wiki = builder.build_wiki()
pipe_spacy = builder.build('spacy')

#imp = GeoWebNewsImporter()
#imp.import_documents(gwn)

gwn.bulk_process(pipe_spacy, saved_steps=['spacy', 'gaz', 'geores', 'clust'], evaluator=ev_res_street)

#gwn.process(pipe_spacy, '13', saved_steps=['spacy'])
# TODO
#gwn.bulk_process(pipe_wiki, saved_steps=['gcnl', 'wikires'], evaluator=ev_res_glob)
#tests.process(pipe, 'global_d_c') , 'geores', 'clust'
