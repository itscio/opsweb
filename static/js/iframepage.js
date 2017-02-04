/**
 * Created by Administrator on 2015/1/4.
 */
function iFrameHeight() {
var ifm= document.getElementById("iframepage");
var subWeb = document.frames ? document.frames["iframepage"].document : ifm.contentDocument;
if(ifm != null && subWeb != null) {
ifm.height = subWeb.body.scrollHeight;
}
}
