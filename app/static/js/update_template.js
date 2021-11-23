function update_init(selector,url,animate=1,key=0) {
  $.ajax({
         type: "GET",
         url: url,
         contentType: 'application/json',
         success: function(result) {
            if (key == 0) {
                $(selector).text(result["count"]);
            }
            else {
                $(selector).text(result["data"][0][key]);
            };
            if (animate) {
                $(selector).counterUp({
                    delay: 10,
                    time: 1000
                });
            };
         },
         error: function(result) {
            console.log(result);
         }
   });
}
