function notify_js(message,type="error",time=5000, placement=false) {
  if (!placement) {
    var placement = {from:"top",align:"right"};
  } else {
    var placement = placement;
  };
  $.notify({
      message: message
    },{
    placement:placement,
    type: type,
    delay:time,
    z_index: 2000,
    timer:time,
    animate: {
      enter: 'animated fadeInRight',
      exit: 'animated fadeOutRight'
    }
  });
}

