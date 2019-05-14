var obj = DDLogin({id:"login_container", goto:"https%3a%2f%2foapi.dingtalk.com", style: "border:none;background-color:white;", width : "230", height: "300"});
var hanndleMessage = function (event) {
var origin = event.origin;
if( origin == "https://login.dingtalk.com" ) {
    var loginTmpCode = event.data;
    var url = encodeURI("https://oapi.dingtalk.com/connect/oauth2/sns_authorize="+loginTmpCode);
    window.location.replace(url);
}
};
if (typeof window.addEventListener != 'undefined') {
    window.addEventListener('message', hanndleMessage, false);
} else if (typeof window.attachEvent != 'undefined') {
    window.attachEvent('onmessage', hanndleMessage);
}
