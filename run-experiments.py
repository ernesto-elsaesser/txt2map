from geoparser import *
from evaluation import *

builder = PipelineBuilder()
builder.spacy_url = 'http://localhost:8001'
builder.cogcomp_url = 'http://localhost:8002'
builder.stanford_url = 'http://localhost:8003'

tr = TopoResolverClient('http://localhost:8004')

# corpora
tests = Corpus('Tests')
gwn = Corpus('GeoWebNews')
lgls = Corpus('LGL-Street')

# evaluators
ev_ner = NEREvaluator()
ev_ner_org = NEREvaluator(groups=['loc', 'org'])
ev_ner_org_per = NEREvaluator(groups=['loc', 'org', 'per'])
ev_ner_org_only = NEREvaluator(groups=['org'])
ev_ner_per_only = NEREvaluator(groups=['per'])
ev_rec = RecogEvaluator()
ev_res = ResolEvaluator()
ev_res_glob = ResolEvaluator(gold_group='geonames')
ev_res_street = ResolEvaluator(gold_group='raw')
ev_res_lgls = ResolEvaluator(gold_group='none')
ev_res_gritta = ResolEvaluator(gold_group='geonames', geonames_by_dist=True) 

pipe = builder.build('stanford')

#imp = GeoWebNewsImporter()
#imp.import_documents(gwn)
# , 'global', 'local'
gwn.bulk_process(pipe, saved_steps=['stanford','topo'], evaluator=ev_res_glob)
#gwn.bulk_process(pipe, saved_steps=['spacy','topo','global','local'] evaluator=ev_res)

#gwn.process(pipe, '312', saved_steps=['spacy','topo','global','local'], evaluator=ev_res)
