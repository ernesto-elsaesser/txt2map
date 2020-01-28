from sklearn.tree import DecisionTreeClassifier
from sklearn.tree.export import export_text
from .datastore import Datastore

class BinaryDecisionTreeClassifier:

  def __init__(self, model_name=None):
    if model_name != None:
      self.dt = Datastore.load_decision_tree(model_name)
    else:
      self.dt = DecisionTreeClassifier(random_state=0) # max_depth=3 min_samples_leaf=5

  def train(self, feature_vectors, classes):
    X = map(self._bool_to_num, feature_vectors)
    y = self._bool_to_num(classes)
    self.dt.fit(X, y)

  def save(self, model_name):
    Datastore.save_decision_tree(model_name, self.dt)

  def print(self, feature_names):
    r = export_text(dt, feature_names=feature_names)
    print(r)

  def predict(self, feature_vector):
    x = self._bool_to_num(feature_vector)
    y_pred = self.dt.predict([x])
    return y_pred[0] == 1

  def _bool_to_num(self, vec):
    return [1 if b else 0 for b in vec]
