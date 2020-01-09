from annotation import *
from evaluation import *


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
ev_161 = Evaluator(tolerance_local=161)
ev = Evaluator()

# pipelines
spacy_full = Pipeline.spacy()
spacy_glob = Pipeline.spacy(local_resol=False)
spacy_gaz = Pipeline.spacy(global_resol=False, local_resol=False)
spacy_only = Pipeline.spacy(use_gazetteer=False, global_resol=False, local_resol=False)

cc_full = Pipeline.cogcomp()
cc_glob = Pipeline.cogcomp(local_resol=False)
cc_gaz = Pipeline.cogcomp(global_resol=False, local_resol=False)
cc_only = Pipeline.cogcomp(use_gazetteer=False, global_resol=False, local_resol=False)

gcnl_gaz = Pipeline.gcnl()
gcnl_only = Pipeline.gcnl(use_gazetteer=False)


#imp_tests.import_documents(tests)
#tests.bulk_process(cc_full, evaluator=ev)

#tests.bulk_process(gcnl_gaz, evaluator=ev_rec)
tests.bulk_process(gcnl_gaz, saved_steps=['tok', 'gcnl', 'loc', 'gaz'], evaluator=ev)
#tests.process(gcnl_gaz, 'global_demonyms_hard', saved_steps=['tok', 'gcnl'])

#gwn.bulk_process(spacy_only, saved_steps=['spacy', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(spacy_gaz, saved_steps=['spacy', 'loc', 'gaz'], evaluator=ev_rec)
#gwn.bulk_process(spacy_glob, saved_steps=['spacy', 'loc', 'gaz', 'geores'], evaluator=ev_161)
#gwn.bulk_process(spacy_full, saved_steps=['spacy', 'loc', 'gaz', 'geores', 'clust'], evaluator=ev_161)

#gwn.bulk_process(cc_only, saved_steps=['tok', 'cogcomp', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(cc_gaz, saved_steps=['tok', 'cogcomp', 'loc', 'gaz'], evaluator=ev_rec)
#gwn.bulk_process(cc_glob, saved_steps=['tok', 'cogcomp', 'loc', 'gaz', 'geores'], evaluator=ev)
#gwn.bulk_process(cc_full, saved_steps=['tok', 'cogcomp', 'loc', 'gaz', 'geores', 'clust'], evaluator=ev_161)

#gwn.bulk_process(gcnl, evaluator=ev_rec)

#gwn.process(cc_only, '160')
