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
ev_rec_noclu = RecogEvaluator(include_osm=False)
ev_rec_ner = RecogEvaluator(layer='ner', include_osm=False)
ev_res = ResolEvaluator()
ev_res_no_osm = ResolEvaluator(tolerance_osm=None)
ev_res_glob = ResolEvaluator(gold_group='gns')
ev_res_street = ResolEvaluator(gold_group='raw')
eval_wiki = WikiResolEvaluator()
eval_wiki_glob = WikiResolEvaluator(gold_group='gns')
eval_wiki_street = WikiResolEvaluator(gold_group='raw')

pipe = builder.build_wiki()
imp = GeoWebNewsImporter()

imp.import_documents(gwn)
#gwn.bulk_process(pipe, saved_steps=['gcnl', 'wikires'], evaluator=eval_wiki_street)
