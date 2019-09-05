"use strict";
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
    el.style.top = (bodyH-elH)/4 + 'px';
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
}
function show_comment(){
    showDialog();
    var comment = $('#comment_show').text();
    $('#comment_update').val(Trim(comment));
}
function work_details_show(url){
        showDialog();
        $.ajax({
         url: url,
         cache: false,
         success: function(html){
             $('#iframe').hide();
             $("#dialog-content").show().html(html);
         }
        });
}

function work_details_iframe(url){
        showDialog();
        $("#dialog-content").hide();
        $('#iframe').show().attr('src',url);
}
function show_k8s_input(name,target_ref,max_update,cpu_update){
    showDialog();
    $('#max_update').val(Trim(max_update));
    $('#cpu_update').val(Trim(cpu_update));
    $('#target_ref').val(Trim(target_ref));
    $('#name').val(Trim(name));
}
//  关闭对话框
function hideDialog(){
    g('dialogMove').style.display = 'none';
    g('mask').style.display = 'none';
}
function hide_comment(){
    g('dialogMove').style.display = 'none';
    g('mask').style.display = 'none';
    $('#dialogDrag').text('修改备注').css('color','');
}
function comment_modify() {
    if ($('#comment_update').val()){
    var comment = $('#comment_update').val()}
    else{
        var comment = ' ';
    }
    var hostname = $('#hostname').text();
    var data = {'comment':comment,'hostname':hostname};
    window.localStorage.setItem('modify_comment_hostname',hostname);
    window.localStorage.setItem('modify_comment_comment',comment);
    $.ajax({
        type: "POST",
        url: "/assets_info/update",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify(data),
        dataType: "json",
        success: function (){
            $('#comment_show').html(comment+'<span style="float: right">' +
                '<a href="javascript:showDialog()" class="mintip" title="修改备注内容"><i class="fas fa-edit"></i>' +
                '</a> &nbsp;' +
                '<a href="javascript:rsync_comment()" class="mintip" title="同步备注信息到Jumpserver">' +
                '<i class="fas fa-sync"></i>' +
                '</a></span>');
            hideDialog()},
        error:function () {$('#dialogDrag').text('修改备注失败');$('#dialogDrag').css('color','red')}
        });

}
function k8s_hpa_modify(name,target_ref) {
    if ($('#max_update').val()){
    var max_update = $('#max_update').val()}
    else{
        var comment = undefined;
    }
    if ($('#cpu_update').val()){
    var cpu_update = $('#cpu_update').val()}
    else{
        var cpu_update = undefined;
    }
    if (max_update && cpu_update){
        var name = $('#name').val();
        var target_ref = $('#target_ref').val();
        var data = {'name':name,'target_ref':target_ref,'max_update':max_update,'cpu_update':cpu_update};
        $.ajax({
        type: "POST",
        url: "/modify_k8s_hpa",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify(data),
        dataType: "json",
        success: function(data){
            if (data['status'] == 'ok'){
                js_msg(data['infos'],3000,'success');
            }else{
                js_msg(data['infos'],3000,'error');
            }
            setTimeout(function (){location.href='/k8s/hpa'},4000);
            },
        }
        );
    }else{
         js_msg('参数不能为空!',3000,'info');
    }
    hideDialog();
}

function k8s_hpa_delete(name) {
        var data = {'name':name};
        $.ajax({
        type: "DELETE",
        url: "/modify_k8s_hpa",
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify(data),
        dataType: "json",
        success: function(data){
            if (data['status'] == 'ok'){
                js_msg(data['infos'],3000,'success');
                setTimeout(function () {
                    location.href='/k8s/hpa';
                },4000);
            }else{
                js_msg(data['infos'],3000,'error');
            }
            },
        }
        );
}