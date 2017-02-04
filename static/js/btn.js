function btn(){
    document.write('<link rel="stylesheet" type="text/css" href="/static/css/loading.css" /><div class="alpha"><div class="spinner"></div><div style="text-align:center;font-weight: bold">该操作执行中,请耐心等待......</div></div>');
    document.onreadystatechange = completeLoading
    if(document.readyState == "complete"){
        document.close();
    };
}