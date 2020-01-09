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
std = Pipeline.standard()

#imp_tests.import_documents(tests)
tests.bulk_exectue(std, evaluator=ev)

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
