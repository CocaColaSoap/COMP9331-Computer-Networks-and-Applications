import java.io.*;
import java.net.*;
import java.util.*;

public class PingClient {
    public static void main(String args[]) throws Exception{
        if (args.length != 2) {
            System.out.println("Required arguments: port");
            return;
        }
        int port = Integer.parseInt(args[1]);
        InetAddress address = InetAddress.getByName(args[0]);
        DatagramSocket socket = new DatagramSocket();
        DatagramPacket response = new DatagramPacket(new byte[1024], 1024);
        long[] List = new long[10];
        for(int i = 1; i <=10 ; i++) {
            String str = "ping " + i;
            byte[] buffer = str.getBytes();
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length, address, port);

            socket.send(packet);
            socket.setSoTimeout(1000);
            long startTime=System.currentTimeMillis();
            while(true){
                try{
                    socket.receive(response);
                    long endTime=System.currentTimeMillis();
                    System.out.println("ping to "+address+", seq = "+i+", rtt = "+(endTime-startTime)+"ms");
                    List[i-1] = endTime - startTime;
                    break;
                }
                catch (SocketTimeoutException e) {
                    System.out.println("ping to "+address+", seq = "+i+", timeout");
                    List[i-1] = 1000;
                    break;
                }
            }
        }
        long max = List[0];
        long min = List[0];
        long  sum = 0;
        long count = 0;
        for(int h = 0;h<10;h++)
        {
            if(List[h] == 1000){
                continue;
            }
            if (max < List[h] || max == 1000){
                max = List[h];
            }
            if (min>List[h]){
                min = List[h]; 
            }
            sum += List[h];
            count += 1;
        }
        if (count != 0){
            long average = sum / count;
            System.out.println("Average Time is "+ average +"ms, Max Time is "+max+ "ms, Min Time is "+min+"ms");
        }
        else
        {
            System.out.println("All packets have no response");
        }
        socket.close();
    }
}
