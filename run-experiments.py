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
spacy_full = Pipeline.standard()
spacy_glob = Pipeline.standard(local_resol=False)
spacy_gaz = Pipeline.standard(global_resol=False, local_resol=False)
spacy_only = Pipeline.standard(use_gazetteer=False, global_resol=False, local_resol=False)
cc_full = Pipeline.standard(use_cogcomp=True, ner_port=8002)
cc_glob = Pipeline.standard(use_cogcomp=True, ner_port=8002, local_resol=False)
cc_gaz = Pipeline.standard(use_cogcomp=True, ner_port=8002, global_resol=False, local_resol=False)
cc_only = Pipeline.standard(use_cogcomp=True, ner_port=8002, use_gazetteer=False, global_resol=False, local_resol=False)


#imp_tests.import_documents(tests)
#tests.bulk_process(cc_full, evaluator=ev)

#gwn.bulk_process(spacy_only, saved_steps=['spacy', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(spacy_gaz, saved_steps=['spacy', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(spacy_glob, saved_steps=['spacy', 'loc', 'gaz', 'geores'], evaluator=ev)
#gwn.bulk_process(spacy_full, saved_steps=['spacy', 'loc', 'gaz', 'geores'], evaluator=ev)

gwn.bulk_process(cc_only, saved_steps=['tok', 'cogcomp', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(cc_gaz, saved_steps=['tok', 'cogcomp', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(cc_glob, saved_steps=['tok', 'cogcomp', 'loc', 'gaz'], evaluator=ev)
#gwn.bulk_process(cc_full, saved_steps=['tok', 'cogcomp', 'loc', 'gaz', 'geores'], evaluator=ev)


#gwn.process(cc_only, '160')
