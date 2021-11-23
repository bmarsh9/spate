/*
$.notify({
	title: '<strong>Heads up!</strong>',
	message: 'You can use any of bootstraps other alert styles as well by default.'
},{
	type: 'success'
});
*/

function ajax_post(url,data) {
  $.ajax({
    type: "POST",
    url: url,
    data: JSON.stringify(data),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function(data){
        return(data)
    },
    error: function(errMsg) {
        return(errMsg);
    }
  })
}
function ajax_get(url) {
  $.ajax({
    type: "GET",
    url: url,
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function(data){
        return JSON.stringify(data)
    },
    error: function(errMsg) {
        return(errMsg);
    }
  })

}

function notify(message,type="success") {
  $.notify({
    message: message
  },{
    type: type,
    animate: {
      enter: 'animated fadeInRight',
      exit: 'animated fadeOutRight'
    }
  });
}
