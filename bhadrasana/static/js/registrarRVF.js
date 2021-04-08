let lacresVerificados = [];
let infracoesEncontradas = [];
let marcasEncontradas = [];
let apreensoesObtidas = [];
let imgList = [];



function registraApreensao() {

    let form = document.querySelector("#registraApreensaoID")

    // Extrai dados do form
    let apreensao = extraiDadosDoForm(form);

    // Cria row com dados da apreensão
    row = criaRow(apreensao);

    //Insere a row na tabela
    let tableBody = document.querySelector("#listaApreensoesBody");
    tableBody.appendChild(row);

    apreensoesObtidas.push(apreensao);

    form.reset();
}

function extraiDadosDoForm(form){

    apreensao = {
        tipo_id: parseInt(form.tipo_id.value),
        tipo_descricao: form.tipo_id.options[form.tipo_id.selectedIndex].text,
        descricao: form.descricao.value,
        peso: parseInt(form.peso.value)
    }
    return apreensao;
}

function criaRow(apreensao){

    let row = document.createElement("tr");
    row.innerHTML = `
        <td class="text-center">${apreensao.tipo_descricao}</td>
        <td class="text-center">${apreensao.peso}</td>
        <td class="text-left">${apreensao.descricao}</td>
        <td class="text-center"><a href="#" onclick="removeRow(this)">x</a></td>
    `;

    return row;
}

function removeRow(objeto){
    objeto.parentElement.parentElement.remove();
    event.preventDefault();
}

function arrayCleaner(array){
    cleanedArray = array.filter(function (el){
        return el != null;
    })
    return cleanedArray;
}

function removeItemOnce(array, value) {
    value = value.replace(/\s+$/, '');
    for( var i = 0; i < array.length; i++){
        if ( array[i] === value) {
            array.splice(i, 1);
        }
    }
    return array;
}

function verificaEnterNoInput(event, contentTag){
    let inputField = event.target;
    if (event.keyCode === 13) {
         let cT = document.querySelector('#' + contentTag);
         let spanTag = document.createElement("span");
         spanTag.classList.add("badge");
         spanTag.classList.add("bg-light");
         spanTag.classList.add("mx-2");
         spanTag.classList.add("text-dark");
         spanTag.innerHTML = `${inputField.value} <a href="#" onclick="removeSpan(event, '${contentTag}')">
         <i class="bi bi-dash-circle-fill"></i></a>`;
         cT.appendChild(spanTag);

         if (contentTag === 'lacresverificadosID'){
            lacresVerificados.push(inputField.value);
         }
         inputField.value = "";
         event.preventDefault();
    }
}

function checkOptionSelection(event, fieldID){
    let selectField = event.target;
    let selectValue = selectField.value;
    let selectOption = selectField.options[selectField.selectedIndex].text
    if (fieldID === '#marca_id'){
        marcasEncontradas.push(selectOption);
        let contentTag = document.querySelector("#marcasEncontradasID");
        addSpan(contentTag, selectOption, '#marca_id', selectValue);
        selectField.selectedIndex = 0;
    }
    if (fieldID === '#infracao_id'){
        infracoesEncontradas.push(selectOption);
        let contentTag = document.querySelector("#infracoesEncontradasID");
        addSpan(contentTag, selectOption, '#infracao_id', selectValue);
        selectField.selectedIndex = 0;
    }
}

function addSpan(contentTag, content, selectField, value){
    let spanTag = document.createElement("span");
    spanTag.classList.add("badge");
    spanTag.classList.add("bg-light");
    spanTag.classList.add("mx-2");
    spanTag.classList.add("text-dark");
    spanTag.classList.add(`${contentTag.id}`);
    spanTag.innerHTML = `${content} <a href="#" onclick="removeSpan(event, '${contentTag.id}', '${content}', '${selectField}', '${value}')">
    <i class="bi bi-dash-circle-fill"></i></a>`;
    contentTag.appendChild(spanTag);
    let sF = document.querySelector(selectField);
    sF.remove(sF.selectedIndex);
}

function removeSpan(event, contentTag, content, selectField, selectValue){
    let cT = document.querySelector('#' + contentTag);
    let sF = document.querySelector(selectField);
    let spanTag = event.currentTarget.parentElement;
    let spanTagContent = spanTag.textContent;
    cT.removeChild(spanTag);

    if (cT.id === 'lacresverificadosID'){
        let inputDestino = document.querySelector("#lacresVerificadosID")
        array = removeItemOnce(lacresVerificados, spanTagContent);
    }

    if (selectField){
        if (sF.id === 'infracao_id'){
        let sV = selectValue;
        let sO = document.createElement("option");
        sO.value = sV;
        sO.text = spanTagContent;
        sF.add(sO);
        array = removeItemOnce(infracoesEncontradas, spanTagContent);
    }

        if (sF.id === 'marca_id'){
            let sV = selectValue;
            let sO = document.createElement("option");
            sO.value = sV;
            sO.text = spanTagContent;
            sF.add(sO);
            array = removeItemOnce(marcasEncontradas, spanTagContent);
        }
    }

    event.preventDefault();
}

function openWindowReload(link) {
    let href = link.href;
    window.open(link,'_self');
    document.location.reload(true);
}


function previewImg(event){
    let filesToUpload = event.target.files;

	for (i = 0; i < filesToUpload.length; i++){
	    let cardGallery = document.querySelector("#cardGallery");
        let cardCol = document.createElement("div");
        cardCol.classList.add("col");
        cardCol.classList.add("dropzone");
        cardCol.setAttribute("draggable", "true");
        cardCol.addEventListener('dragstart', handleDragStart, false);
        cardCol.addEventListener('dragover', handleDragOver, false);
        cardCol.addEventListener('dragenter', handleDragEnter, false);
        cardCol.addEventListener('dragleave', handleDragLeave, false);
        cardCol.addEventListener('dragend', handleDragEnd, false);
        cardCol.addEventListener('drop', handleDrop, false);
        cardCol.innerHTML = `
            <div class="card border-0" style="cursor: move;">
                <img id="img" class="card-img-top" style="width:300px; height: 200px"/>
                <div class="card-img-overlay text-end">
                    <a class="card-title text-end text-white" style="cursor: default" onclick="removeElement(this.parentElement)">
                        <i class="bi bi-x-circle-fill"></i>
                    </a>
                </div>
            </div>
        `
        cardGallery.appendChild(cardCol);
        let image = document.getElementById("img");
        img.id = "img-"+[i];
        let file = filesToUpload[i];
        let reader = new FileReader();
        reader.onload = function(){
            image.src = reader.result;
            image.name = file.name;
        }
        reader.readAsDataURL(file);
	}
}

function removeElement(element){
    element.parentElement.parentElement.remove();
}

function handleDragStart(e) {
    dragSrcEl = this;

    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
  }

function handleDragEnd(e) {
    this.classList.remove('border');
}

function handleDragOver(e) {
    this.classList.add('border');
    if (e.preventDefault) {
      e.preventDefault();
    }

    return false;
  }

function handleDragEnter(e) {
    this.classList.add('border');
}

function handleDragLeave(e) {
    this.classList.remove('border');
}

function handleDrop(e) {
  e.stopPropagation();

    if (dragSrcEl !== this) {
      dragSrcEl.innerHTML = this.innerHTML;
      this.innerHTML = e.dataTransfer.getData('text/html');
    }
    this.classList.remove('border');
    return false;
}

function extractDocImgs(){
    let docImgs = document.images;
    for (let i = 0; i < docImgs.length; i++) {
        if (docImgs[i].id != ""){
            let id = docImgs[i].id;
            let name = docImgs[i].name;
            let content = docImgs[i].src;

            imgObj = {
                id: id,
                name: name,
                content: content
            }
            imgList.push(imgObj);
        }
    }
    return imgList;
}

//function extractBlob(){
//    for (let i = 0; i < imgList.length; i++){
//        fetch(imgList[i].content)
//        .then(res => res.blob())
//        .then(blob => {
//            imgList[i].content = blob;
//            imgList[i].size = blob.size;
//            imgList[i].type = blob.type;
//        });
//    }
//    return imgList;
//}

//function extractImgContent(){
//    for (let i = 0; i < imgList.length; i++){
//        let reader = new FileReader();
//        reader.onload = function(){
//            imgList[i].content = reader.result;
//        }
//    reader.readAsDataURL(imgList[i].content);
//    }
//    return imgList;
//}

function registraRVF(){

    extractDocImgs();

    let token = document.getElementsByName("csrftoken")[0].content;
    let inspecaonaoinvasiva = document.querySelector("#inspecaonaoinvasiva");
    let ovr_id = document.querySelector("#ovr_id").textContent;
    let redirectBtn = document.querySelector("#redirectBtn");
    if (inspecaonaoinvasiva.checked){
        inspecaonaoinvasiva = 1;
    }
    else {
        inspecaonaoinvasiva = 0;
    }

    const data = {
        ovr_id: document.querySelector("#ovr_id").textContent,
        numeroCEmercante: document.querySelector("#numeroCEmercante").value,
        numerolote: document.querySelector("#numerolote").value,
        peso: document.querySelector("#peso").value,
        peso_manifestado: document.querySelector("#peso_manifestado").value,
        volume: document.querySelector("#volume").value,
        inspecaonaoinvasiva: inspecaonaoinvasiva,
        adata: document.querySelector("#adata").value,
        ahora: document.querySelector("#ahora").value,
        descricao: document.querySelector("#descricao").value,
        lacresVerificados: lacresVerificados,
        infracoesEncontradas: infracoesEncontradas,
        marcasEncontradas: marcasEncontradas,
        apreensoesObtidas: apreensoesObtidas,
        imagensRecebidas: imgList
    };
    const url = '/registrar_rvf';

    fetch(url, {
      method: 'POST',
      redirect: 'follow',
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, multipart/form-data, text-plain, */*",
        "X-CSRF-TOKEN": token
      },
      body: JSON.stringify(data),
    })

    .then((response) => {
        if (response.ok) {
            alert('RVF registrada com sucesso')
        }
        return response.json();
    })

    .then((json) => {
        let url = '/consultar_rvf?id='+json['id'];
        window.location.href = url;
    })

    .catch((error) => {
      console.error('Error:', error);
    });
}
