//  获取元素对象
function g(id){
    return document.getElementById(id);
}
//  自动居中元素（el = Element）
function autoCenter( el ){
    var bodyW = document.documentElement.clientWidth;
    var bodyH = document.documentElement.clientHeight;
    var elW = el.offsetWidth;
    var elH = el.offsetHeight;
    el.style.left = (bodyW-elW)/2 + 'px';
    el.style.top = (bodyH-elH)/2 + 'px';
}
//  自动扩展元素到全部显示区域
function fillToBody( el ){
    el.style.width  = document.documentElement.clientWidth  +'px';
    el.style.height = document.documentElement.clientHeight + 'px';
}
function Trim(str) {
        return str.replace(/(^\s*)|(\s*$)/g, "");
    }
function showDialog(){
    g('dialogMove').style.display = 'block';
    g('mask').style.display = 'block';
    autoCenter( g('dialogMove') );
    fillToBody( g('mask') );
    var comment = $('#comment_show').text();
    $('#comment_update').val(Trim(comment));
}
//  关闭对话框
function hideDialog(){
    g('dialogMove').style.display = 'none';
    g('mask').style.display = 'none';
    $('#dialogDrag').text('修改备注');
    $('#dialogDrag').css('color','');
}
function comment_modify() {
    if ($('#comment_update').val()){
    var comment = $('#comment_update').val()}
    else{
        var comment = ' ';
    };
    var hostname = $('#hostname').text();
    var data = {'comment':comment,'hostname':hostname};
    $.ajax({
        type: "POST",
        url: "/assets_info/update",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify(data),
        dataType: "json",
        success: function (){
            $('#comment_show').html(comment+'<a href="javascript:showDialog()" class="current" style="float: right">&nbsp;&nbsp;<i class="fas fa-edit"></i></a>');
            hideDialog()},
        error:function () {$('#dialogDrag').text('修改备注失败');$('#dialogDrag').css('color','red')}
        });

};