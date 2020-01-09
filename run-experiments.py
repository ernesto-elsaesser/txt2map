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
cc_full = Pipeline.standard(use_cogcomp=True, ner_port=8002)
spacy_only = Pipeline.standard(global_resol=False, local_resol=False)
cc_only = Pipeline.standard(use_cogcomp=True, ner_port=8002, global_resol=False, local_resol=False)

#imp_tests.import_documents(tests)
tests.bulk_process(cc_full, evaluator=ev)
#gwn.bulk_process(cc_only, saved_steps=['tok', 'cogcomp', 'loc'], evaluator=ev_rec)
#gwn.bulk_process(spacy_only, saved_steps=['spacy', 'loc'], evaluator=ev_rec)
#gwn.process(cc_only, '160')

'''
tests.annotate_all(cogcomp)
tests.annotate_all(cogcomp_gaz)
tests.annotate_all(cogcomp_t2m)
tests.evaluate_all(cogcomp_t2m, ev_res)

tests.annotate_all(spacy)
tests.annotate_all(spacy_gaz)
tests.annotate_all(spacy_t2m)
tests.evaluate_all(spacy_t2m, ev_rec)
'''
