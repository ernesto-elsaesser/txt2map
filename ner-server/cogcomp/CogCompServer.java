import edu.illinois.cs.cogcomp.ner.LbjTagger.*;
import org.apache.commons.io.IOUtils;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.InetAddress;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

public class CogCompServer {

  public static void main(String[] args) throws Exception {

    try {
      Parameters.readConfigAndLoadExternalData("ner.properties", false);
    } catch (IOException e) {
      System.out.println("Initialization failed!");
      return;
    }

    ParametersForLbjCode.currentParameters.forceNewSentenceOnLineBreaks = true;
    NETagPlain.init();

    int port = Integer.parseInt(args[0]);
    InetAddress addr = InetAddress.getByName("0.0.0.0");
    InetSocketAddress saddr = new InetSocketAddress(addr, port);
    HttpServer server = HttpServer.create(saddr, 0);
    server.createContext("/", new PostHandler());
    server.setExecutor(null); // default executor

    System.out.println("CogComp NER server listening on port " + args[0]);
    server.start();
  }

  static class PostHandler implements HttpHandler {

    @Override
    public void handle(HttpExchange t) throws IOException {

      InputStream is = t.getRequestBody();
      String text = IOUtils.toString(is, "UTF-8");

      String responseText = null;
      int statusCode = 0;

      try {
        responseText = NETagPlain.tagLine(text);
        statusCode = 200;
      } catch(Exception e) {
        responseText = e.toString();
        statusCode = 500;
        e.printStackTrace();
        System.out.println(e);
      } 

      byte[] response = responseText.getBytes();
      t.sendResponseHeaders(statusCode, response.length);
      OutputStream os = t.getResponseBody();
      os.write(response);
      os.close();
    }
  }
}
