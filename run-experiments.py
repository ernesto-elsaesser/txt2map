from annotation import *
from evaluation import *

builder = PipelineBuilder()

# corpora
tests = Corpus('Tests')
gwn = Corpus('GeoWebNews')
lgl = Corpus('LGL')

# importers
imp_tests = TestsImporter()
imp_gwn = GeoWebNewsImporter()
imp_lgl = LGLImporter()

# evaluators
ev_rec = Evaluator(resol=False)
ev = Evaluator()
ev_161 = Evaluator(tolerance_local=161)
ev_wiki = Evaluator(count_wiki=True)

pipe = builder.build('spacy')
# imp_tests.import_documents(tests)
#tests.bulk_process(cc_full, evaluator=ev)

#tests.bulk_process(gcnl_gaz, evaluator=ev_rec)
#tests.bulk_process(gcnl, saved_steps=['tok', 'gcnl', 'loc', 'gaz'], evaluator=ev)
#tests.process(gcnl_gaz, 'global_demonyms_hard', saved_steps=['tok', 'gcnl'])

gwn.bulk_process(pipe, saved_steps=['spacy', 'loc', 'gaz', 'geores'], evaluator=ev_161)
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
