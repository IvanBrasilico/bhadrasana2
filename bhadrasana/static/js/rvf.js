function exclui_anexo(anexo_id){
    $.getJSON('exclui_anexo', {
     _id: anexo_id
    }, function(anexos) {
      // mostra_anexos(anexos);
    });
    location.reload();
}
function upload_files(ev){
// Resize images before upload if images are too big
    // Set the image once loaded into file reader
    // Load files into file reader
    console.log($("input#images"));
    console.log($("input#images").val());
    var filesToUpload = $("input#images")[0].files;
    console.log(filesToUpload);
    var dataurl = null;
    for (var i = 0; i < filesToUpload.length; i++) {
        console.log(i);
        file = filesToUpload[i];
        var reader = new FileReader();
        reader.fileName = file.name;
        reader.onloadend = function(e)
        {
            var img = document.createElement("img");
            img.src = e.target.result;
            img.onload = function () {
                var canvas = document.createElement("canvas");
                var ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0);
                var MAX_WIDTH = 2592;
                var MAX_HEIGHT = 1944;
                var width = img.width;
                var height = img.height;
                if (width > height) {
                  if (width > MAX_WIDTH) {
                    console.log('width bigger');
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                  }
                } else {
                  if (height > MAX_HEIGHT) {
                    console.log('height bigger');
                    width *= MAX_HEIGHT / height;
                    height = MAX_HEIGHT;
                  }
                }
                canvas.width = width;
                canvas.height = height;
                console.log(width, height);
                var ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, width, height);
                dataurl = canvas.toDataURL("image/jpeg");
                // Post the data
                var fd = new FormData();
                fd.append("filename", e.target.fileName);
                fd.append("content", dataurl);
                let rvf_id = document.querySelector("#rvfid").textContent;
                fd.append("rvf_id",  rvf_id);
                $.ajax({
                    url: 'api/rvf_imgupload',
                    data: fd,
                    cache: false,
                    contentType: false,
                    processData: false,
                    type: 'POST',
                    success: function(data){
                    //location.reload(true);
                    }
                });
            }
            img.onload()
        }
        reader.readAsDataURL(file);
    }
    //
}
function update_ordem_arquivos(){
    var qttd_arq = $("#div_imagens").children().length;
    let rvf_id = document.querySelector("#rvfid").textContent;
    var lista = []

    $('#div_imagens').children('span').each(function(){
        lista.push($(this).attr("name"));
    });
    /*for (i = 0; i < lista.length; i++){
        console.log(lista[i]);
    }
    console.log(qttd_arq);
    console.log(rvf_id);
    */
    $.getJSON('rvf_inclui_ordem_arquivos', {
      rvf_id: rvf_id, qttd_arq: qttd_arq, lista: lista
    });
}
