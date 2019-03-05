/*jshint node:true */
var datatable_config = {
           "sProcessing": "处理中...",
           "sLengthMenu": "显示 _MENU_ 项结果",
           "sZeroRecords": "没有匹配结果",
           "sInfo": "显示第 _START_ 至 _END_ 项结果，共 _TOTAL_ 项",
           "sInfoEmpty": "显示第 0 至 0 项结果，共 0 项",
           "sInfoFiltered": "(由 _MAX_ 项结果过滤)",
           "sInfoPostFix": "",
           "sSearch": "结果内搜索:",
           "sUrl": "",
           "sEmptyTable": "表中数据为空",
           "sLoadingRecords": "载入中...",
           "sInfoThousands": ",",
           "oPaginate": {
               "sFirst": "首页",
               "sPrevious": "上页",
               "sNext": "下页",
               "sLast": "末页"},
           "oAria": {
               "sSortAscending": ": 以升序排列此列",
               "sSortDescending": ": 以降序排列此列"}
            };
function referrer_url() {
    if (document.referrer) {
        var url = document.referrer;
    } else {
        var url = '/index';
    }
    location.href = url;
}
function countDown(secs,url){
    var jumpTo = document.getElementById('jumpTo');
    jumpTo.innerHTML=secs;
    if(--secs>0){
     setTimeout("countDown("+secs+",'"+url+"')",1000);
     }
    else{
     location.href=url;
     }
    }
function selectdevice() {
	var v = document.getElementById('select_device').value;
	if (v == 'server'){
	    var m = document.getElementById('select_action').value;
        if (m == 'modify'){
                document.getElementById('old_host').style.display = '';

            } else {
                document.getElementById('old_host').style.display = 'None';
            }
		document.getElementById('device_type').style.display = 'None';
		document.getElementById('idrac').style.display = '';

	}
	else {
		document.getElementById('device_type').style.display = '';
		document.getElementById('idrac').style.display = 'None';
		document.getElementById('old_host').style.display = 'None'
	}
}
function selectaction() {
    var m = document.getElementById('select_device').value;
	var v = document.getElementById('select_action').value;
	if (v == 'modify'){
	    if (m == 'server'){
	        document.getElementById('old_host').style.display = '';

        } else {
	        document.getElementById('old_host').style.display = 'None';
        }
        if (document.getElementById('discovery')){
	        document.getElementById('assets_manage').style.marginLeft = '5%';
	        document.getElementById('discovery').style.display = '';
        }else{
	        document.getElementById('assets_manage').style.marginLeft = '25%';
        }
        document.getElementById('file_upload').style.display = 'None';
		document.getElementById('fault').style.display = '';
		document.getElementById('rack').style.width = '11%';
		document.getElementById('rack').removeAttribute("readonly");
		document.getElementById('devicetype').removeAttribute("readonly");
		document.getElementById('rack').setAttribute("placeholder","可选,鼠标悬停提示");
		document.getElementById('devicetype').setAttribute("placeholder","可选");
		document.getElementById('input_purch').setAttribute("placeholder","可选,点击选择日期");
        document.getElementById('input_expird').setAttribute("placeholder","可选,点击选择日期");
	}
	if (v == 'down'){
	    if (document.getElementById('discovery')){
	        document.getElementById('assets_manage').style.marginLeft = '5%';
	        document.getElementById('discovery').style.display = '';
        }else{
	        document.getElementById('assets_manage').style.marginLeft = '25%';
        }
	    document.getElementById('file_upload').style.display = 'None';
		document.getElementById('fault').style.display = 'None';
		document.getElementById('old_host').style.display = 'None';
		document.getElementById('rack').style.width = '18.5%';
		document.getElementById('rack').setAttribute("readonly","readonly");
		document.getElementById('devicetype').setAttribute("readonly","readonly");
		document.getElementById('idrac_down').setAttribute("readonly","readonly");
		document.getElementById('rack').setAttribute("placeholder","勿填");
        document.getElementById('devicetype').setAttribute("placeholder","勿填");
        document.getElementById('idrac_down').setAttribute("placeholder","勿填");
        document.getElementById('input_purch').setAttribute("placeholder","勿选");
        document.getElementById('input_expird').setAttribute("placeholder","勿选");
	}
	if (v == 'add') {
	    if (document.getElementById('discovery')){
	        document.getElementById('assets_manage').style.marginLeft = '5%';
	        document.getElementById('discovery').style.display = '';
        }else{
	        document.getElementById('assets_manage').style.marginLeft = '25%';
        }
	    document.getElementById('file_upload').style.display = 'None';
		document.getElementById('fault').style.display = 'None';
		document.getElementById('old_host').style.display = 'None';
        document.getElementById('rack').style.width = '18.5%';
        document.getElementById('rack').removeAttribute("readonly");
		document.getElementById('devicetype').removeAttribute("readonly");
		document.getElementById('idrac_down').removeAttribute("readonly");
        document.getElementById('rack').setAttribute("placeholder","必选,鼠标悬停提示");
        document.getElementById('devicetype').setAttribute("placeholder","必选");
        document.getElementById('idrac_down').setAttribute("placeholder","idrac ip 可选");
        document.getElementById('input_purch').setAttribute("placeholder","必选,点击选择日期");
        document.getElementById('input_expird').setAttribute("placeholder","必选,点击选择日期");
	}
	if (v == 'upload') {
	    document.getElementById('assets_manage').style.marginLeft = '5%';
	    document.getElementById('file_upload').style.display = '';
	    if (document.getElementById('discovery')){
	      document.getElementById('discovery').style.display = 'None';
        }
	}
}
function obj_display(project_id){
    if (document.getElementById(project_id).style.display) {
        document.getElementById(project_id).style.display = "";
    }
    else
    {
      document.getElementById(project_id).style.display="none";
    }
}
function form_hide() {
    document.getElementById('new_add').style.display = 'none';
    document.getElementById('add').style.display = '';
}
function get_url(url,id,args){
    $.get(url+id+'?resource_type='+args);
    document.getElementById(id).style.display='none';
    document.getElementById('add').style.display='none';
    document.getElementById('new_add').style.display = 'none';
}
function error_select(id,url) {
    var v = document.getElementById(id).value;
    if (v !='None'){
        $.get(url+'/'+v);
        location.href =url;
    }
}
function set_cookies(id) {
    var v = document.getElementById(id).value;
    if (v !='None'){
        $.cookie(id,v,{path:'/'});
        window.location.reload();
    }
}
function get_uri_lists(id) {
    var v = document.getElementById(id).value;
    var uri = window.location.pathname;
    if (v !='None'){
        $.cookie(id,v,{path:'/'});
        business_change_select(v);
        if ('/chart_business_bigdata' == uri){
            window.location.reload();
        };
    }
}
function select_host_set_cookies(host,uri) {
        var host = host.split(',')[0];
        $.cookie("business_bigdata_select_host",host,{path:'/'});
        $.cookie("business_bigdata_select_uri", '', { expires: -1 ,path:'/'});
        window.location.href = uri;
}
function select_buy_date(){
    if ($('#select').val() == 'buy_date'){
        document.getElementById("input").flatpickr({locale: "zh",mode: "range",maxDate:'today', dateFormat: "Y-m-d"});
        document.getElementById("input").setAttribute("placeholder","点击选取日期");
    }else{
        var input_content = $('#input').val();
        document.getElementById("input").flatpickr({noCalendar:true,allowInput:true,locale: "zh"});
        if (input_content){
            $('#input').val(input_content);
        }else{
            document.getElementById("input").setAttribute("placeholder","自动进行精确或模糊查询");
        };
    }
}
function business_change_select(host) {
    var searchs = new Array();
    var id = "#business_bigdata_select_uri";
    var uri = $.cookie('business_bigdata_select_uri');
    $.ajax({url:"/get_business_bigdata/"+host,dataType : "json",success:
            function(data) {$(id).empty();$.each(data['results'],
                function(i,val){
                    var option = "<option value='"+val+"'>"+val+"</option>";
                    searchs.push({'id':i.toString(),'text':val});
                    $(id).append(option);});
                    if (data['results'].indexOf(uri) >=0){
                        $(id).val(uri);
                    }else{
                        $(id).val(data['results'][0]);
                    };
                    $.input_uri('business_bigdata_select_uri',searchs);
            }});
    }

function ajax_url(url) {
    spop({
        template: '操作执行中......',
        style: 'info',
        position:'top-center',
        autoclose: false,
        group:'msg'
        });
    $.ajax({url:url,success:function(data){if (data['status'] == 'ok'){
            spop({
            template: data['infos'],
            style: 'success',
            position:'top-center',
            autoclose: 3000,
            group:'msg',
            });
            }else{
            spop({
            template: data['infos'],
            style: 'error',
            position:'top-center',
            autoclose: 3000,
            group:'msg',
            });
            };
            }});
}
function js_msg(msg,autoclose,style) {
    spop({
        template:msg,
        style: style,
        position:'top-center',
        autoclose: autoclose,
        group:'msg'
        });
}

function execute_rollback() {
    var execute = $('#execute').val();
    if (execute=='rollback'){
        $('#package_type').attr("disabled",true);
        $('#publish_type').attr("disabled",true);
        $('#restart').attr("disabled",true);
        $('#gray').attr("disabled",true);
        $('#check_url').attr("disabled",true);
        $('#package_md5').attr("disabled",true);
        $('#path').hide();
        $('#input_text').hide();
        $('#input_describe').hide();
        $('#rollback_select').show();
    } else{
        $('#package_type').attr("disabled",false);
        $('#publish_type').attr("disabled",false);
        $('#restart').attr("disabled",false);
        $('#gray').attr("disabled",false);
        $('#check_url').attr("disabled",false);
        $('#package_md5').attr("disabled",false);
        $('#path').show();
        $('#input_text').show();
        $('#input_describe').show();
        $('#rollback_select').hide();
    }
}
function get_version(id) {
    var project = $('#'+id).val();
    var url = "/get_project_version/"+project;
    $.ajax({url:url,success:function(data){
        if (data['results'] != 'null'){
            $('#version').empty();
            $.each(data['results'],
            function(i,val){
                var option = "<option value='"+val+"'>"+val+"</option>";
                $('#version').append(option);});
        }}
    })
}
function table_data(id) {
    $('#'+id).DataTable({
        language: datatable_config,
        "lengthMenu": [[50,100,-1],[50,100,'all']],
        "iDisplayLength":50
        });
}
function table_less(id) {
    $('#'+id).DataTable({
        language: datatable_config,
        "lengthMenu": [[20,50,-1],[20,50,'all']],
        "iDisplayLength":20
        });
}
function table_order(id,col) {
    $('#'+id).DataTable({
        "order": [[ col, "desc" ]],
        "lengthMenu": [[50,100,-1],[50,100,'all']],
        "iDisplayLength":50,
        language: datatable_config
        });
}

function token_url(url) {
    var excute = url.split('/')[2];
    if (excute == 'add'){
        var platform = $('#input_platform').val();
        if(platform == ''){
            js_msg('平台名称未填写',1500,'error');
            }
        else{
            var expire = $('#select_date').val();
            $.ajax(
                {url:url+'/'+expire+'/'+platform,
                    success:function(data){
                    if (data == 'success'){
                        js_msg('授权操作成功',1500,'success');}
                        else{
                        js_msg('授权操作失败',1500,'error');
                    }
                }
                });
            }
        };
    if (excute == 'modify'){
        var id = url.split('/')[3];
        var expire_date = $('#'+id).val();
        $.ajax({url:(url+'/'+expire_date),success:function(data){
                    if (data == 'success'){
                        js_msg('修改操作成功',1500,'success');}
                        else{
                        js_msg('修改操作失败',1500,'error');
                    }}
                });
        };
    if (excute == 'drop'){
        $.ajax({url:(url),success:function(data){
            if (data == 'success'){
                js_msg('吊销操作成功',1500,'success');}
                else{
                    js_msg('吊销操作失败',1500,'error');
                }
            }
            });
        };
    setTimeout(function(){window.location.reload();},1500);
}
function select_chart_list(id){
    var name = id.split('_')[0];
    if (id.indexOf('list') >=0){
        var new_id = name+'_chart';
        $('#'+id).hide();
        $('#'+new_id).show();
    };
    if (id.indexOf('chart') >=0){
        var new_id = name+'_list';
        $('#'+id).hide();
        $('#'+new_id).show();
    };
}