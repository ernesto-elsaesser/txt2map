from geoparser import Config
from evaluation import GeoWebNewsImporter, CorpusAnnotator, SpacyPipeline, GCNLPipeline, GCNLT2MPipeline, SpacyT2MPipeline, CorpusEvaluator

importer = GeoWebNewsImporter()
annotator = CorpusAnnotator('GeoWebNews')
evaluator = CorpusEvaluator('GeoWebNews', True, 161)

spacy = SpacyPipeline(use_server=True)
gcnl = GCNLPipeline()
spacy_geo = SpacyT2MPipeline()

#importer.import_documents()
#annotator.annotate_all(ner)
#annotator.annotate_all(spacy_geo)
evaluator.evaluate_all(spacy_geo.id_)
