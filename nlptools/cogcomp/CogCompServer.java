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

    NETagPlain.init();

    System.out.println("Starting server on port " + args[1]);
    int port = Integer.parseInt(args[1]);
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
      String response = "";

      try {
        response = NETagPlain.tagLine(text);
      } catch(Exception e) {} 

      t.sendResponseHeaders(200, response.length());
      OutputStream os = t.getResponseBody();
      os.write(response.getBytes());
      os.close();
    }
  }
}
