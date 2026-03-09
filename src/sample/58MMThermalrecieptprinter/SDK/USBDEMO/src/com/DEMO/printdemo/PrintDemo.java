package com.zj.printdemo;


import com.zj.usbsdk.UsbController;
import com.zj.usbsdk.PrintPic;
import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.app.Activity;
import android.hardware.usb.UsbDevice;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;


public class PrintDemo extends Activity {
    private Button btn_conn = null;
    private Button btnSend = null;
    private Button btn_test = null;
    private Button btnClose = null;
    private EditText txt_content = null;
    
    //private int VID = 0x1CBE;
    //private int PID = 0x0003;
    private int[][] u_infor;
    UsbController  usbCtrl = null;
    UsbDevice dev = null;
    
	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.main);
		btn_conn = (Button)findViewById(R.id.btn_conn);
		btnSend = (Button)findViewById(R.id.btnSend);
		btn_test = (Button)findViewById(R.id.btn_test);
		btnClose = (Button)findViewById(R.id.btnClose);
		txt_content = (EditText)findViewById(R.id.txt_content);
		
		btn_conn.setOnClickListener(new ClickEvent());
		btnSend.setOnClickListener(new ClickEvent());
		btn_test.setOnClickListener(new ClickEvent());
		btnClose.setOnClickListener(new ClickEvent());
		
    	btnSend.setEnabled(false);
    	btn_test.setEnabled(false);
    	btnClose.setEnabled(false);
		
		usbCtrl = new UsbController(this,mHandler);
		u_infor = new int[6][2];
		u_infor[0][0] = 0x1CBE;
		u_infor[0][1] = 0x0003;
		u_infor[1][0] = 0x1CB0;
		u_infor[1][1] = 0x0003;
		u_infor[2][0] = 0x0483;
		u_infor[2][1] = 0x5740;
		u_infor[3][0] = 0x0493;
		u_infor[3][1] = 0x8760;
		u_infor[4][0] = 0x0416;
		u_infor[4][1] = 0x5011;
                u_infor[5][0] = 0x0416;
		u_infor[5][1] = 0xAABB;
	}

    @Override
    public void onDestroy() {
        super.onDestroy();
        usbCtrl.close();
    }
    
    //检查是否具有访问usb设备的权限
    public boolean CheckUsbPermission(){
		if( dev != null ){
			if( usbCtrl.isHasPermission(dev)){
				return true;
			}
		}
		btnSend.setEnabled(false);
		btn_test.setEnabled(false);
		btnClose.setEnabled(false);
		btn_conn.setEnabled(true);
		Toast.makeText(getApplicationContext(), getString(R.string.msg_conn_state),
                Toast.LENGTH_SHORT).show();
    	return false;
    }
    
	private final  Handler mHandler = new Handler() {
		@Override
        public void handleMessage(Message msg) {
            switch (msg.what) {
            case UsbController.USB_CONNECTED:
            	Toast.makeText(getApplicationContext(), getString(R.string.msg_getpermission),
                        Toast.LENGTH_SHORT).show();
            	btnSend.setEnabled(true);
            	btn_test.setEnabled(true);
            	btnClose.setEnabled(true);
            	btn_conn.setEnabled(false);
            	break;
            default:
            	break;
            }
        }
    };
    
    //按钮点击事件
	class ClickEvent implements View.OnClickListener {
		public void onClick(View v) {
			byte isHasPaper;
			if( v == btn_conn ){
				usbCtrl.close();
				int  i = 0;
				for( i = 0 ; i < 6 ; i++ ){
					dev = usbCtrl.getDev(u_infor[i][0],u_infor[i][1]);
					if(dev != null)
						break;
				}
				
    			if( dev != null ){
    				if( !(usbCtrl.isHasPermission(dev))){
    					//Log.d("usb调试","请求USB设备权限.");
    					usbCtrl.getPermission(dev);
    				}else{
    	            	Toast.makeText(getApplicationContext(), getString(R.string.msg_getpermission),
    	                        Toast.LENGTH_SHORT).show();
    	            	btnSend.setEnabled(true);
    	            	btn_test.setEnabled(true);
    	            	btnClose.setEnabled(true);
    	            	btn_conn.setEnabled(false);
    				}
    			}
			}else if( v == btnSend ){
				isHasPaper = usbCtrl.revByte(dev);
				if( isHasPaper == 0x38 ){
					Toast.makeText(getApplicationContext(), "The printer has no paper",
	                        Toast.LENGTH_SHORT).show();
					return;
				}
				String txt_msg = txt_content.getText().toString();
                if( CheckUsbPermission() == true ){
                	usbCtrl.sendMsg(txt_msg, "GBK", dev);
                }
			}else if( v == btn_test ){
                String msg = "";
                String lang = getString(R.string.strLang);
            	byte[] cmd = new byte[3];
        	    cmd[0] = 0x1b;
        	    cmd[1] = 0x21;
				
				isHasPaper = usbCtrl.revByte(dev);
				if( isHasPaper == 0x38 ){
					Toast.makeText(getApplicationContext(), "The printer has no paper",
	                        Toast.LENGTH_SHORT).show();
					return;
				}
				printImage();
            	if((lang.compareTo("en")) == 0){	
            		cmd[2] |= 0x10;
            		usbCtrl.sendByte(cmd, dev);    //倍宽、倍高模式
            		usbCtrl.sendMsg("Congratulations!\n", "GBK", dev);
            		cmd[2] &= 0xEF;        
            		usbCtrl.sendByte(cmd, dev);     //取消倍高、倍宽模式
            		msg = "  You have sucessfully created communications between your device and our usb printer.\n\n"
                          +" Our company is a high-tech enterprise which specializes" +
                          " in R&D,manufacturing,marketing of thermal printers and barcode scanners.\n\n";
            		usbCtrl.sendMsg(msg, "GBK", dev);
            	}else if((lang.compareTo("ch")) == 0){
            		cmd[2] |= 0x10;    
            		usbCtrl.sendByte(cmd, dev);   //倍宽、倍高模式
            		usbCtrl.sendMsg("恭喜您！\n", "GBK", dev);
            		cmd[2] &= 0xEF;
            		usbCtrl.sendByte(cmd, dev);   //取消倍高、倍宽模式
            		msg = "  您已经成功的连接上了我们的usb打印机！\n\n"
            		+ "  我们公司是一家专业从事研发，生产，销售商用票据打印机和条码扫描设备于一体的高科技企业.\n\n";
            		usbCtrl.sendMsg(msg, "GBK", dev);
            	}
			}else if( v == btnClose ){
				usbCtrl.close();
            	btnSend.setEnabled(false);
            	btn_test.setEnabled(false);
            	btnClose.setEnabled(false);
            	btn_conn.setEnabled(true);
			}
		}
	}
	
    //打印图形
	private void printImage() {
    	int i = 0,s = 0,j = 0,index = 0;
    	byte[] temp = new byte[56];
		byte[] sendData = null;
    	PrintPic pg = new PrintPic();
    	pg.initCanvas(384);     
    	pg.initPaint();
    	pg.drawImage(0, 0, "/mnt/sdcard/icon.jpg");
    	sendData = pg.printDraw();
        
    	for( i = 0 ; i < pg.getLength() ; i++ ){  //每隔一行加上包头，发送一次数据
    		s = 0;
    		temp[s++] = 0x1D;
    		temp[s++] = 0x76;
    		temp[s++] = 0x30;
    		temp[s++] = 0x00;
    		temp[s++] = (byte)(pg.getWidth() / 8);
    		temp[s++] = 0x00;
    		temp[s++] = 0x01;
    		temp[s++] = 0x00;
    		for( j = 0 ; j < (pg.getWidth() / 8) ; j++ )
    			temp[s++] = sendData[index++];
    		usbCtrl.sendByte(temp, dev); 
    	}
    }	
}
