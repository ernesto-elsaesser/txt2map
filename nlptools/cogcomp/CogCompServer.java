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
      Parameters.readConfigAndLoadExternalData("conll.properties", false);
    } catch (IOException e) {
      System.out.println("Initialization failed!");
      return;
    }

    ParametersForLbjCode.currentParameters.forceNewSentenceOnLineBreaks = true;
    NETagPlain.init();

    System.out.println("Starting server on port " + args[0]);
    int port = Integer.parseInt(args[0]);
    InetAddress addr = InetAddress.getByName(null);
    InetSocketAddress saddr = new InetSocketAddress(addr, port);
    HttpServer server = HttpServer.create(saddr, 0);
    server.createContext("/", new PostHandler());
    server.setExecutor(null); // creates a default executor
    server.start();
  }

  static class PostHandler implements HttpHandler {

    @Override
    public void handle(HttpExchange t) throws IOException {

      InputStream is = t.getRequestBody();
      String text = IOUtils.toString(is, "UTF-8");

      String tagged_text = "";
      try {
        tagged_text = NETagPlain.tagLine(text);
        String in_len = Integer.toString(text.length());
        String out_len = Integer.toString(tagged_text.length());
        System.out.println("TAGGED " + in_len + " > " + out_len);
      } catch(Exception e) {
        e.printStackTrace();
        System.out.println(e);
      } 

      byte[] response = tagged_text.getBytes();
      t.sendResponseHeaders(200, response.length);
      OutputStream os = t.getResponseBody();
      os.write(response);
      os.close();
    }
  }
}
