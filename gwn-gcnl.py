from evaluation import GCNLAnnotator

annotator = GCNLAnnotator(update=False)
evaluator = GeoWebNewsEvaluator(annotator)
evaluator.test_all()
#evaluator.test(30)
