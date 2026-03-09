package com.zj.zjwfprinter;

import android.app.Activity;  
import android.os.Bundle;  
import android.os.Handler;
import android.os.Message;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;
import com.zj.wfsdk.*;

public class PrintDemo extends Activity {
    Button btnConn = null;
	Button btnPrint = null;
	Button btn_test = null;
	Button btnClose = null;
	Button btn_opencasher = null;
	EditText edtContext = null;
	WifiCommunication wfComm = null;
	EditText txt_ip = null;
	int  connFlag = 0;
	revMsgThread revThred = null;
	//checkPrintThread cheThread = null;
	private static final int WFPRINTER_REVMSG = 0x06;
	
	@Override  
	public void onCreate(Bundle savedInstanceState){  
	    super.onCreate(savedInstanceState);  
	    setContentView(R.layout.main);
	    btnConn = (Button) this.findViewById(R.id.btn_conn); 
	    btnConn.setOnClickListener(new ClickEvent());
	    btnPrint = (Button) this.findViewById(R.id.btnSend);
	    btnPrint.setOnClickListener(new ClickEvent());
	    btn_test = (Button) this.findViewById(R.id.btn_test);
	    btn_test.setOnClickListener(new ClickEvent());
	    btnClose = (Button) this.findViewById(R.id.btnClose);
	    btnClose.setOnClickListener(new ClickEvent());
	    edtContext = (EditText) this.findViewById(R.id.txt_content);
	    txt_ip = (EditText)this.findViewById(R.id.txt_ip);
	    wfComm = new WifiCommunication(mHandler);
	    btn_opencasher = (Button)this.findViewById(R.id.btn_opencasher);
	    btn_opencasher.setOnClickListener(new ClickEvent());
	    
	    btnConn.setEnabled(true);
	    btnPrint.setEnabled(false);
	    btn_test.setEnabled(false);
	    btnClose.setEnabled(false);
	    btn_opencasher.setEnabled(false);
	}   
	  
	@Override
	protected void onDestroy() {
		super.onDestroy();
		wfComm.close();
	}
	  
	class ClickEvent implements View.OnClickListener {
		public void onClick(View v) {
			if (v == btnConn) {	
				if( connFlag == 0 ){   //避免连续点击此按钮创建多个连接线程
					connFlag = 1;
				    Log.d("wifi调试","点击\"连接\"");
				    String strAddressIp = txt_ip.getText().toString();
				    wfComm.initSocket(strAddressIp,9100);
				}
			} else if (v == btnPrint) {
                String msg = edtContext.getText().toString();
                if( msg.length() > 0 ){
           			byte[] tcmd = new byte[3];
        			tcmd[0] = 0x10;
        			tcmd[1] = 0x04;
        			tcmd[2] = 0x04;     //检测是否有纸指令
                    wfComm.sndByte(tcmd);
                	wfComm.sendMsg(msg,"gbk");
                    byte[] tail = new byte[3];
                    tail[0] = 0x0A;
                    tail[1] = 0x0D;
                    wfComm.sndByte(tail);
                }
			} else if (v == btnClose) {
				wfComm.close();
			}else if( v == btn_opencasher ){ 
       			byte[] tcmd = new byte[5];
    			tcmd[0] = 0x1B;
    			tcmd[1] = 0x70;
    			tcmd[2] = 0x00;     
    			tcmd[3] = 0x40;   
    			tcmd[4] = 0x50;   
    			wfComm.sndByte(tcmd);
			}else if (v == btn_test) { 
    			byte[] tcmd = new byte[4];
    			tcmd[0] = 0x10;
    			tcmd[1] = 0x04;
    			tcmd[2] = 0x04;     
                wfComm.sndByte(tcmd);   //检测是否有纸指令
                
                tcmd[0] = 0x1B;
                tcmd[1] = 0x42;
                tcmd[2] = 0x04;
                tcmd[3] = 0x01;
                wfComm.sndByte(tcmd);   //蜂鸣器鸣叫
                
				String msg = "";
                String lang = getString(R.string.strLang);
				printImage();           //打印图片
            	byte[] cmd = new byte[3];        
        	    cmd[0] = 0x1b;
        	    cmd[1] = 0x21;
            	if((lang.compareTo("en")) == 0){	
            		cmd[2] |= 0x10;
            		wfComm.sndByte(cmd);          //set double height and double width mode
            		wfComm.sendMsg("Congratulations! \n\n", "GBK");
            		cmd[2] &= 0xEF;        
            		wfComm.sndByte(cmd);          //cancel double height and double width mode
            		try {
        				Thread.sleep(50);                   //每发一次延时5毫秒
        			} catch (InterruptedException e) {
        				e.printStackTrace();
        			} 
            		msg = "  You have sucessfully created communications between your device and our WIFI printer.\n\n"
                          +"  our company is a high-tech enterprise which specializes" +
                          " in R&D,manufacturing,marketing of thermal printers and barcode scanners.\n\n";
            		wfComm.sendMsg(msg, "GBK");
            	}else if((lang.compareTo("ch")) == 0){
            		cmd[2] |= 0x10;
            		wfComm.sndByte(cmd);             //set double height and double width mode
            		wfComm.sendMsg("恭喜您! \n\n", "GBK");  //send data to the printer By gbk encoding
            		cmd[2] &= 0xEF;                 
            		wfComm.sndByte(cmd);            //cancel double height and double width mode
            		try {
        				Thread.sleep(50);                   //每发一次延时5毫秒
        			} catch (InterruptedException e) {
        				e.printStackTrace();
        			} 
            		msg = "  您已经成功的连接上了我们的WIFI打印机！\n\n"
            		+ "  我们公司是一家专业从事研发，生产，销售商用票据打印机和条码扫描设备于一体的高科技企业.\n\n";
            		wfComm.sendMsg(msg, "GBK");
            	}
            	
				tcmd[0]=0x1D;
				tcmd[1]=0x56;
				tcmd[2]=0x42;
				tcmd[3]=90;   
				wfComm.sndByte(tcmd);  //切刀指令
			}
		}
	}  
	
    private final  Handler mHandler = new Handler() {
        @Override
        public void handleMessage(Message msg) {
            switch (msg.what) {
            case WifiCommunication.WFPRINTER_CONNECTED:
            	connFlag = 0;
            	Toast.makeText(getApplicationContext(), "Connect the WIFI-printer successful",
                        Toast.LENGTH_SHORT).show();
        	    btnPrint.setEnabled(true);
        	    btn_test.setEnabled(true);
        	    btnClose.setEnabled(true);
        	    btn_opencasher.setEnabled(true);
        	    btnConn.setEnabled(false);
        	    
        	    revThred = new revMsgThread();
        	    revThred.start();
            	break;
            case WifiCommunication.WFPRINTER_DISCONNECTED:
            	Toast.makeText(getApplicationContext(), "Disconnect the WIFI-printer successful",
                        Toast.LENGTH_SHORT).show();
    		    btnConn.setEnabled(true);
			    btnPrint.setEnabled(false);
			    btn_test.setEnabled(false);
			    btnClose.setEnabled(false);
			    btn_opencasher.setEnabled(false);
			    revThred.interrupt();
            	break;
            case WifiCommunication.SEND_FAILED:
            	connFlag = 0;
            	Toast.makeText(getApplicationContext(), "Send Data Failed,please reconnect",
                        Toast.LENGTH_SHORT).show();
    		    btnConn.setEnabled(true);
			    btnPrint.setEnabled(false);
			    btn_test.setEnabled(false);
			    btnClose.setEnabled(false);
			    btn_opencasher.setEnabled(false);
			    revThred.interrupt();
            	break;
            case WifiCommunication.WFPRINTER_CONNECTEDERR:
            	connFlag = 0;
            	Toast.makeText(getApplicationContext(), "Connect the WIFI-printer error",
                        Toast.LENGTH_SHORT).show();
            	break;
            case WFPRINTER_REVMSG:
            	byte revData = (byte)Integer.parseInt(msg.obj.toString());
            	if(((revData >> 6) & 0x01) == 0x01)
            		Toast.makeText(getApplicationContext(), "The printer has no paper",Toast.LENGTH_SHORT).show();    
                break;
            default:
                break;
            }
        }
    };
    
    class checkPrintThread extends Thread {
    	@Override
    	public void run() {
			byte[] tcmd = new byte[3];
			tcmd[0] = 0x10;
			tcmd[1] = 0x04;
			tcmd[2] = 0x04;
    		try {
                while(true){
				    wfComm.sndByte(tcmd);
				    Thread.sleep(15);
				    Log.d("wifi调试","发送一次调试数据");
                }
    		}catch (InterruptedException e){
				e.printStackTrace();
				Log.d("wifi调试","退出线程");
    		}
    	}
    }
    
    //打印机线程，连接上打印机时创建，关闭打印机时退出
	class revMsgThread extends Thread {	
		@Override
		public void run() {            
			try {
				Message msg = new Message();
				int revData;
				while(true)
	            {
					revData = wfComm.revByte();               //非阻塞单个字节接收数据，如需改成非阻塞接收字符串请参考手册
					if(revData != -1){
						
						msg = mHandler.obtainMessage(WFPRINTER_REVMSG);
		                msg.obj = revData;
		                mHandler.sendMessage(msg);
					}    
				    Thread.sleep(20);
	            }
			} catch (InterruptedException e) {
				e.printStackTrace();
				Log.d("wifi调试","退出线程");
			}
		}
	}
    
	
    //打印图形
	private void printImage() {
		byte[] sendData = null;
    	PrintPic pg = new PrintPic();
    	int i = 0,s = 0,j = 0,index = 0,lines = 0;
    	pg.initCanvas(384);     
    	pg.initPaint();
    	pg.drawImage(0, 0, "/mnt/sdcard/icon.bmp");
    	sendData = pg.printDraw();
    	byte[] temp = new byte[(pg.getWidth() / 8)*5];
    	byte[] dHeader = new byte[8];
    	if(pg.getLength()!=0){
    		dHeader[0] = 0x1D;
        	dHeader[1] = 0x76;
        	dHeader[2] = 0x30;
        	dHeader[3] = 0x00;
        	dHeader[4] = (byte)(pg.getWidth()/8);
        	dHeader[5] = 0x00;
        	dHeader[6] = (byte)(pg.getLength()%256);
        	dHeader[7] = (byte)(pg.getLength()/256);
        	wfComm.sndByte(dHeader); 	
	    	for( i = 0 ; i < (pg.getLength()/5)+1 ; i++ ){         //每过5行发送一次图片数据
	    		s = 0;
	    		if( i < pg.getLength()/5 ){
	    			lines = 5;
	    		}else{
	    			lines = pg.getLength()%5;
	    		}
	    		for( j = 0 ; j < lines*(pg.getWidth() / 8) ; j++ ){
	    			temp[s++] = sendData[index++];
	    		}
	    		wfComm.sndByte(temp); 
	    		try {
					Thread.sleep(60);                              //每发一次延时60毫秒
				} catch (InterruptedException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				} 
	    		for(j = 0 ; j <(pg.getWidth()/8)*5 ; j++ ){         //将缓存清零
				    temp[j] = 0;
			    }
	    	}
    	}
    }	
}



