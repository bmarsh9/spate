function ajax_get(selector,url) {
    $.ajax({
         type: "GET",
         url: url,
         contentType: 'application/json',
         success: function(options) {
             //try to remove spinner
             var id = 'div#loader-'+selector
             $( id ).remove();
             try {
               var chart = new ApexCharts(document.querySelector("#"+selector), options);
               chart.render();
               return("ok")
             } catch(err) {
               console.log(err)
               $( "#"+selector ).html('<div id="alert-icon" style="text-align:center !important;"><i class="text-danger" data-feather="alert-triangle"></i> No Data</div>')
               feather.replace()
             }
         },
         error: function(result) {
            //change spinner on error
            console.log(result);
         }
    });
}

function apex_render(selector,url) {
    //load spinner
    var id = 'loader-'+selector
    $( "#"+selector ).append("<div id="+id+" class='loader'></div>");
    ajax_get(selector,url);
}

