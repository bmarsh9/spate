function notify_js(message,type="error",time=5000) {
  $.notify({
      message: message
    },{
    type: type,
    delay:5000,
    z_index: 2000,
    timer:time,
    animate: {
      enter: 'animated fadeInRight',
      exit: 'animated fadeOutRight'
    }
  });
}


