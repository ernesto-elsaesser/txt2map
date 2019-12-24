from geoparser import Config
from .annotator import T2MAnnotator
from .evaluator import GoldAnnotation, CorpusEvaluator


class TestEvaluator:

  def __init__(self):
    Config.recog_large_ner_model = False
    self.annotator = T2MAnnotator(update=True)
    self.eval = CorpusEvaluator(False, 1)

  def run_all(self):
    for title in self.tests:
      self.run(title)

    print(f'--- FINISHED ---')
    print(self.eval.metrics_str())

  def run(self, title):
    data = self.tests[title]
    text = data['text']
    annotations = data['anns']

    print(f'--- {title} ---')
    doc = self.annotator.annotated_doc('Tests', title, text)
    self.eval.start_document(doc)

    for name, lat, lon, geoname_id in annotations:
      pos = text.find(name)
      a = GoldAnnotation(pos, name, lat, lon, geoname_id)
      self.eval.evaluate(a)

    if 'expect_none' in data:
      recs = doc.get('rec')
      if len(recs) > 0:
        print('{title} test failed - toponyms recognized!')


  tests = {
      'global_default_sense': {
          'text': 'I love Paris.',
          'anns': [('Paris', 0, 0, 2988507)]
      },
      'global_onto_sim': {
          'text': 'I love Paris in Lamar County, Texas.',
          'anns': [('Paris', 0, 0, 4717560), ('Lamar County', 0, 0, 4705086), ('Texas', 0, 0, 4736286)]
      },
      'global_onto_sim_hard': {
          'text': 'The University in San Marcos in California is one of many in America.',
          'anns': [('San Marcos', 0, 0, 5392368),
                   ('California', 0, 0, 5332921),
                   ('America', 0, 0, 6252001)]
      },
      'global_top_defaults': {
          'text': '''France is in Europe and California in the United States.
              Africa is a continent and Mexico and Uruguay are countries.''',
          'anns': [('France', 0, 0, 3017382),
                   ('Europe', 0, 0, 6255148),
                   ('California', 0, 0, 5332921),
                   ('United States', 0, 0, 6252001),
                   ('Africa', 0, 0, 6255146),
                   ('Mexico', 0, 0, 3996063),
                   ('Uruguay', 0, 0, 3439705)],
      },
      'global_name_sim': {
          'text': 'The Mall of Asia in Paranaque City.',
          'anns': [('Paranaque City', 0, 0, 1694782),
                   ('Mall of Asia', 14.5349995, 120.9832017, None)],
          'note': 'there is a big one spelled with ñ and a small one without'
      },
      'global_abbrevs': {
          'text': 'It\'s nice in Calif.',
          'anns': [('Calif.', 0, 0, 5332921)]
      },
      'global_d_c': {
          'text': 'The capital of the U.S. is Washington, D.C. (not the state).',
          'anns': [('U.S.', 0, 0, 6252001),
                   ('Washington, D.C.', 0, 0, 4140963)]
      },
      'global_person': {
          'text': 'Peter King is not a toponym.',
          'anns': [],
          'expect_none': True
      },
      'global_demonyms': {
          'text': 'Che Guevara is burried in the Cuban city of Santa Clara.',
          'anns': [('Santa Clara', 0, 0, 3537906)]
      },
      'global_demonyms_hard': {
          'text': 'The Kurdish fighters keep up the resistance.',
          'anns': [('Kurdish', 0, 0, 298795)]
      },
      'global_two': {
          'text': 'Paris in in France and Los Angeles in California.',
          'anns': [('Paris', 0, 0, 2988507), ('France', 0, 0, 3017382),
                   ('Los Angeles', 0, 0, 5368361), ('California', 0, 0, 5332921)]
      },
      'ancestors': {
          'text': 'Avoyelles task force arrests 14. They live in Cottonport, US.',
          'anns': [('Avoyelles', 0, 0, 4315243), ('Cottonport', 0, 0, 4320874)]
      },
      'embedded': {
          'text': 'He is from South Africa.',
          'anns': [('South Africa', 0, 0, 953987)]
      },
      'local_node': {
          'text': 'We met at Checkpoint Charlie in Berlin.',
          'anns': [('Checkpoint Charlie', 52.5075075, 13.3903737, None)]
      },
      'local_way': {
          'text': 'When in Los Angeles check out Hollywood Blvd.',
          'anns': [('Los Angeles', 0, 0, 5368361),
                   ('Hollywood Blvd', 34.101596, -118.338724, None)]
      },
      'local_relation': {
          'text': 'The Statue of Liberty is in New York.',
          'anns': [('Statue of Liberty', 40.689167, -74.044444, None)]
      },
      'local_abbrevs': {
          'text': 'He painted St. Peter\'s Basilica in Rome.',
          'anns': [('St. Peter\'s Basilica', 41.90216, 12.4536, None)]
      },
      'local_abbrevs_2': {
          'text': 'On N. Bedford Drive in Beverly Hills.',
          'anns': [('N. Bedford Drive', 34.0678280, -118.4049976, None)]
      }
  }


