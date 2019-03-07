var obj = DDLogin({id:"login_container", goto:"https%3a%2f%2foapi.dingtalk.com%2fconnect%2foauth2%2fsns_authorize%3fappid%3ddingoa7wymhx6dbeffjels%26response_type%3dcode%26scope%3dsnsapi_login%26state%3dSTATE%26redirect_uri%3dhttp%3a%2f%2f172.16.68.13%2flogin", style: "border:none;background-color:white;", width : "230", height: "300"});
var hanndleMessage = function (event) {
var origin = event.origin;
if( origin == "https://login.dingtalk.com" ) {
    var loginTmpCode = event.data;
    var url = encodeURI("https://oapi.dingtalk.com/connect/oauth2/sns_authorize?appid=dingoa7wymhx6dbeffjels&response_type=code&scope=" +
        "nsapi_login&state=STATE&redirect_uri=http://172.16.68.13/login&loginTmpCode="+loginTmpCode);
    window.location.replace(url);
}
};
if (typeof window.addEventListener != 'undefined') {
    window.addEventListener('message', hanndleMessage, false);
} else if (typeof window.attachEvent != 'undefined') {
    window.attachEvent('onmessage', hanndleMessage);
}