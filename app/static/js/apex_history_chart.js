function ajax_history_get(selector,url) {
    $.ajax({
         type: "GET",
         url: url,
         contentType: 'application/json',
         success: function(options) {
//             console.log(options);
//             console.log(JSON.stringify(options))
             //try to remove spinner
             var id = 'div#loader-'+selector
             $( id ).remove();
             try {
               var chart = new ApexCharts(document.querySelector("#"+selector), options);
               chart.render().then(() => {
                 for (let i = 1; i <= chart.w.globals.series[0].length; i++) {
                   const datapoint = chart.w.config.series[0].data[i - 1];
                   console.log(datapoint)
                   if (datapoint["y"] < 3) {
                     var img = "face_1.png"
                   } else if (datapoint["y"] < 5) {
                     var img = "face_2.png"
                   } else if (datapoint["y"] < 7) {
                     var img = "face_3.png"
                   } else if (datapoint["y"] < 9) {
                     var img = "face_4.png"
                   } else {
                     var img = "face_5.png"
                   }
                   //var img_url = "https://192.168.1.212/static/img/faces/"+img
                   var img_url = "/static/img/faces/"+img

                   chart.addPointAnnotation({
                     x: datapoint.x,
                     y: datapoint.y,
                     marker: {
                       size: 0
                     },
                     image: {
                       path: img_url,
                       offsetY: -10
                     }
                   });
                 }
               });
               return("ok")
             } catch(err) {
               console.log(err)
               $( "#"+selector ).html('<div id="alert-icon" style="text-align:center !important;"><i style="color:#f4a100;" data-feather="alert-triangle"></i> No Data</div>')
               feather.replace()
             }

         },
         error: function(result) {
            //change spinner on error
            console.log(result);
         }
    });
}

function apex_history_render(selector,url) {
    //load spinner
    var id = 'loader-'+selector
    $( "#"+selector ).append("<div id="+id+" class='loader'></div>");
    //setTimeout(2000);
    ajax_history_get(selector,url);
}

