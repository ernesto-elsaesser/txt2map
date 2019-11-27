import os
import logging
import csv
import json
from .evaluator import CorpusEvaluator


class SampleEvaluator:

  def __init__(self):
    self.eval = CorpusEvaluator(1)

  def start(self):
    self.eval.start_corpus('Samples')

  def test_osm_point(self):
    text = 'We met at Checkpoint Charlie in Berlin.'
    self.eval.start_document('OSM Point Test', text)
    self.eval.test_gold_coordinates(10, 'Checkpoint Charlie', 52.5075075, 13.3903737)
    self.eval.finish_document()

  def test_osm_polygon(self):
    text = 'The Statue of Liberty is in New York.'
    self.eval.start_document('OSM Polygon Test', text)
    self.eval.test_gold_coordinates(4, 'Statue of Liberty', 40.689167, -74.044444)
    self.eval.finish_document()

  def finish(self):
    self.eval.finish_corpus()
