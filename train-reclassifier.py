from sklearn.ensemble import RandomForestClassifier
from geoparser import Datastore, Layer, Reclassifier, ReclassificationFeatureExtractor
from evaluation import Corpus, Evaluator

ner_key = 'spacy' # NER tool to optimize for
corpus = Corpus('GeoWebNews')

cache_key = 'ent-classes-' + ner_key
if Datastore.data_available(cache_key, in_cache=True):

  data = Datastore.load_data(cache_key, from_cache=True)
  feature_vectors = data[0]
  target_classes = data[1]

else:

  extractor = ReclassificationFeatureExtractor()
  dummy_eval = Evaluator()
  feature_vectors = []
  target_classes = []

  for doc_id in corpus.document_ids():
    gold_doc = corpus.get_gold_document(doc_id)
    doc = corpus.get_document(doc_id, [ner_key])

    gold_positions = gold_doc.annotations_by_position(Layer.gold)

    for a in doc.get_all(Layer.ner):
      if a.group not in Reclassifier.classes:
        continue

      feature_vector = extractor.feature_vector(doc, a)
      target_class = 0
      if a.pos in gold_positions:
        g = gold_positions[a.pos]
        if g.group == 'geonames':
          if not dummy_eval.matches(a, g):
            continue # name boundary error, bad training example
          geoname = Datastore.get_geoname(g.data)
          if geoname.fcl in ['P', 'A']:
            target_class = 1

      feature_vectors.append(feature_vector)
      target_classes.append(target_class)

  data = [feature_vectors, target_classes]
  Datastore.save_data(cache_key, data, to_cache=True)

rf = RandomForestClassifier(n_estimators=100, oob_score=True, random_state=0)
rf.fit(feature_vectors, target_classes)
print('OOB score:', rf.oob_score_)
Datastore.save_object('ner-reclf', rf)
