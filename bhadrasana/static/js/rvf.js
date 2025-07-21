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
    var filesToUpload = $("input#images")[0].files;
    var dataurl = null;

    var quantidadeTotalDeImagens = filesToUpload.length;
    var quantidadeDeImagensCarregadas =  0;
    //var listaNomeImagens = [];
    var listaDataModificacao = [];

    console.log(`Quantidade de imagens: ${quantidadeTotalDeImagens}`);

    for (var i = 0; i < filesToUpload.length; i++) {
        console.log(i);

        let file = filesToUpload[i];
        console.log(`Data criacao do arquivo: ${file.lastModifiedDate}`);
        // listaNomeImagens.push(file.name);
        listaDataModificacao.push(file.lastModifiedDate.toISOString());
        var reader = new FileReader();
        reader.fileName = file.name;
        reader.onloadend = function(e)
        {
            var img = document.createElement("img");
            img.src = e.target.result;
            img.onload = function () {
                setTimeout(() =>{
                    //getExif(img);
                    var canvas = document.createElement("canvas");
                    var ctx = canvas.getContext("2d");
                    ctx.drawImage(img, 0, 0);
                    var MAX_WIDTH = 2592;
                    var MAX_HEIGHT = 1944;
                    var width = img.width;
                    var height = img.height;
                    if (width > height) {
                      if (width > MAX_WIDTH) {
                        height *= MAX_WIDTH / width;
                        width = MAX_WIDTH;
                      }
                    } else {
                      if (height > MAX_HEIGHT) {
                        width *= MAX_HEIGHT / height;
                        height = MAX_HEIGHT;
                      }
                    }
                    canvas.width = width;
                    canvas.height = height;
                    var ctx = canvas.getContext("2d");
                    ctx.drawImage(img, 0, 0, width, height);
                    dataurl = canvas.toDataURL("image/jpeg");
                    // Post the data
                    var fd = new FormData();
                    fd.append("filename", e.target.fileName);
                    fd.append("content", dataurl);
                    fd.append("dataModificacao", file.lastModifiedDate.toISOString());
                    let rvf_id = document.querySelector("#rvfid").textContent;
                    fd.append("rvf_id",  rvf_id);
					
					//let dataurl = canvas.toDataURL("image/jpeg", 0.92);
					console.log("Comprimento da string base64:", dataurl.length);

                    $.ajax({
                        url: 'api/rvf_imgupload',
                        data: fd,
                        cache: false,
                        contentType: false,
                        processData: false,
                        type: 'POST',

						error: function(xhr, status, err) {
							if (xhr.status === 413) {
								// recupera o nome do arquivo que está no FormData
								var nome = fd.get('filename');
								alert('Upload falhou: a imagem "' + nome + '" excede o tamanho máximo permitido.');
							} else {
								alert('Erro ao enviar imagem: ' + (err || xhr.statusText));
							}
						},

                        success: function(data){
                            quantidadeDeImagensCarregadas++;
                            console.log(`Carregou imagem: ${quantidadeDeImagensCarregadas}`);

                            //Verifica se todas as imagens foram carregadas
                            if (quantidadeDeImagensCarregadas == quantidadeTotalDeImagens){

                                listaDataModificacao.sort();
                                console.dir(listaDataModificacao);
                                //Atualiza ordem das imagens no banco
                                $.getJSON(
                                    'rvf_ordena_por_data_criacao',
                                    {
                                        rvf_id: rvf_id, qttd_arq: quantidadeTotalDeImagens, lista: listaDataModificacao
                                    },
                                    // Success
                                    function(){
                                        location.reload(true);
                                    }
                                );
                            }
                        }
                    });
                });
            }
            //img.onload()
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
