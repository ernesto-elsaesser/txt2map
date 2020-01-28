from sklearn.tree import DecisionTreeClassifier
from geoparser import Datastore, Layer, Reclassifier, ReclassificationFeatureExtractor, BinaryDecisionTreeClassifier
from evaluation import Corpus, Evaluator

ner_key = 'spacy'
corpus = Corpus('GeoWebNews')
feature_vectors = []
target_classes = []

dummy_eval = Evaluator()
extractor = ReclassificationFeatureExtractor()

for doc_id in corpus.document_ids():
  gold_doc = corpus.get_gold_document(doc_id)
  doc = corpus.get_document(doc_id, [ner_key])

  gold_positions = gold_doc.annotations_by_position(Layer.gold)

  for a in doc.get_all(Layer.ner):
    if a.group not in Reclassifier.classes:
      continue

    feature_vector = extractor.feature_vector(doc, a)
    target_class = False
    if a.pos in gold_positions:
      g = gold_positions[a.pos]
      if g.group == 'geonames':
        if not dummy_eval.matches(a, g):
          continue # name boundary error, bad training example
        geoname = Datastore.get_geoname(g.data)
        target_class = geoname.fcl in ['P', 'A']

    feature_vectors.append(feature_vector)
    target_classes.append(target_class)


clf = BinaryDecisionTreeClassifier()
clf.train(feature_vectors, target_classes)

clf.save('entrecl')

clf.print(extractor.feature_names())

#species = np.array(y_test).argmax(axis=1)
#predictions = np.array(y_pred).argmax(axis=1)
#confusion_matrix(species, predictions)

#tree.plot_tree(dt)
