from sklearn.ensemble import RandomForestClassifier
from .datastore import Datastore

class BooleanFeatureClassifier:

  def __init__(self, model_name=None):
    if model_name != None:
      self.dt = Datastore.load_object(model_name)
    else:
      self.dt = RandomForestClassifier(n_estimators=100, oob_score=True, random_state=0)

  def train(self, feature_vectors, target_classes):
    self.dt.fit(feature_vectors, target_classes)

  def save(self, model_name):
    Datastore.save_object(model_name, self.dt)

  def predict(self, feature_vector):
    y_pred = self.dt.predict([feature_vector])
    return y_pred[0] == 1

