from .store import DocumentStore


class Corpus:

  def __init__(self, corpus_name, gold_key='gold'):
    self.corpus_name = corpus_name
    self.gold_key = gold_key

  def annotate_all(self, annotator, doc_range=None):
    paths = DocumentStore.doc_ids(self.corpus_name)
    num_docs = len(paths)
    doc_range = doc_range or range(len(paths))

    print(f'---- START ANNOTATION: {annotator.key} ----')
    for i in doc_range:
      doc_id = paths[i]
      print(f'-- {doc_id} ({i+1}/{num_docs}) --')
      m = self.annotate_one(annotator, doc_id)
    print(f'---- END ANNOTATION ----')

  def annotate_one(self, annotator, doc_id):
    doc = annotator.annotate(self.corpus_name, doc_id)
    DocumentStore.save_annotations(self.corpus_name, doc_id, annotator.key, doc)

  def evaluate_all(self, annotator, evaluator):
    paths = DocumentStore.doc_ids(self.corpus_name)
    num_docs = len(paths)

    print(f'---- START EVALUATION: {annotator.key} / {self.gold_key} ----')
    for i, doc_id in enumerate(paths):
      print(f'-- {doc_id} ({i+1}/{num_docs}) --')
      m = self.evaluate_one(annotator, evaluator, doc_id)

    print(f'---- END EVALUATION ----')
    evaluator.log_total()

  def evaluate_one(self, annotator, evaluator, doc_id):
    doc = DocumentStore.load_doc(self.corpus_name, doc_id, annotator.key)
    target_doc = DocumentStore.load_doc(self.corpus_name, doc_id, self.gold_key)

    rec_anns = doc.annotations_by_position('rec')
    res_anns = doc.annotations_by_position('res')
    gold_anns = target_doc.get('gld')

    result = evaluator.evaluate(rec_anns, res_anns, gold_anns)
    evaluator.log(result)
    return result
