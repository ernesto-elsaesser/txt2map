import edu.stanford.nlp.ie.AbstractSequenceClassifier;
import edu.stanford.nlp.ie.crf.*;
import edu.stanford.nlp.ling.CoreLabel;

import org.apache.commons.io.IOUtils;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.InetAddress;
import java.util.List;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

public class StanfordServer {

  public static void main(String[] args) throws Exception {

    PostHandler handler = null;
    try {
      handler = new PostHandler();
    } catch (IOException e) {
      System.out.println("Initialization failed!");
      e.printStackTrace();
      System.out.println(e);
      return;
    }

    int port = Integer.parseInt(args[0]);
    InetAddress addr = InetAddress.getByName("0.0.0.0");
    InetSocketAddress saddr = new InetSocketAddress(addr, port);
    HttpServer server = HttpServer.create(saddr, 0);
    server.createContext("/", handler);
    server.setExecutor(null); // default executor

    System.out.println("Stanford NER server listening on port " + args[0]);
    server.start();
  }

  static class PostHandler implements HttpHandler {

    AbstractSequenceClassifier<CoreLabel> classifier;

    public PostHandler() throws Exception {
      String model = "lib/english.conll.4class.distsim.crf.ser.gz";
      this.classifier = CRFClassifier.getClassifier(model);
    }

    @Override
    public void handle(HttpExchange t) throws IOException {

      InputStream is = t.getRequestBody();
      String text = IOUtils.toString(is, "UTF-8");

      String responseText = "";
      for (List<CoreLabel> lcl : classifier.classify(text)) {
        for (CoreLabel cl : lcl) {
          responseText += cl.originalText() + "\t";
          responseText += Integer.toString(cl.beginPosition()) + "\t";
          responseText += cl.ner() + "\n";
        }
      }

      byte[] response = responseText.getBytes();
      t.sendResponseHeaders(200, response.length);
      OutputStream os = t.getResponseBody();
      os.write(response);
      os.close();
    }
  }
}
