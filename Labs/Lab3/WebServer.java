import java.util.*;
import java.net.*;
import java.io.*;
public class WebServer {
    public static void main(String args[]) {
        if (args.length != 1) {
            System.out.println("Required arguments: Port");
        }
        int port = Integer.parseInt(args[0]);
        try {
            ServerSocket server = new ServerSocket(port);//start server by typing the port
            System.out.println("Server starts at "+port);
            while (true) {
                Socket socket = server.accept();//begin to accept the request from the browser
                System.out.println("detect a connection from" + socket.getInetAddress() + socket.getPort());
                response(socket);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void response(Socket socket) {
        try {
            InputStream input = socket.getInputStream();
            BufferedReader bf = new BufferedReader(new InputStreamReader(input));
            String[] line = bf.readLine().split(" ");
            OutputStream outSocket = socket.getOutputStream();
            if (line[0].equals("GET")) {//determine whether the request method is GET or not.
                if (!line[1].equals("/")){//determine whether the browser requests nothing or file.
                    String file = line[1].substring(1);
                        try {
                            FileInputStream in = new FileInputStream(new File(file));
                            //load file
                            outSocket.write("HTTP/1.1 200 OK\n".getBytes());
                            if (file.endsWith(".html")) {
                                outSocket.write("Content-Type: text/html; charset=UTF-8\n\n".getBytes());
                            }
                            else if(file.endsWith(".png")){
                                outSocket.write("Content-Type: image/png; charset=UTF-8\n\n".getBytes());
                            }
                            else if(file.endsWith(".jpeg")||(file.endsWith("jpg"))){
                                outSocket.write("Content-Type: image/jpeg; charset=UTF-8\n\n".getBytes());
                            }
                            else if(file.endsWith(".gif")){
                                outSocket.write("Content-Type: image/gif; charset=UTF-8\n\n".getBytes());
                            }
                            else{
                                outSocket.write("Content-Type: application/html; charset=UTF-8\n\n".getBytes());
                            }
                            //write header and Content-Type
                            byte[] htmlbuffer = new byte[in.available()];
                            if (in != null) {
                                int len = 0;
                                while ((len = in.read(htmlbuffer)) != -1) {
                                    outSocket.write(htmlbuffer, 0, len);
                                }
                            }
                            in.close();
                            outSocket.close();
                            socket.close();
                        }catch (FileNotFoundException f){
                        outSocket.write("HTTP/1.1 404 Not Found\n".getBytes());
                        outSocket.write("Content-Type: text/html; charset=UTF-8\n\n".getBytes());
                        outSocket.write(("<html>\n" +
                                "<body>\n" +
                                "<h1>404 Not Found!</h1>\n"+
                                "</body>\n" +
                                "</html>\n").getBytes());
                        outSocket.flush();
                        outSocket.close();
                        }
                       
                    }
                }
                else{
                    outSocket.write("HTTP/1.1 404 Not Found\n".getBytes());
                    outSocket.write("Content-Type: text/html; charset=UTF-8\n\n".getBytes());
                    outSocket.write(("<html>\n" +
                            "<body>\n" +
                            "<h1>404 Not Found!</h1>\n"+
                            "</body>\n" +
                            "</html>\n").getBytes());
                    outSocket.flush();
                    outSocket.close();
                }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
