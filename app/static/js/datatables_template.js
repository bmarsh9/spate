/* Description: Quickly render datatables graph Usage: index.html
  <html>
    <body>
      <div class="card-body">
        <div class="table-responsive">
          <table id="example" class="table table-striped table-bordered" style="width:100%">
            <thead><tr></tr></thead>
          </table>
        </div>
      </div>
      <script>
        $(document).ready(function (){
            $.noConflict(); // remove this if not required
            // draw datatable
            var table = dt_init(
                selector="#example", // table id selector
                url = "/api/agent/data/users?as_datatables=true&inc_fields=id,email,active", // data url source
                dt_ajax=0, // 1=render columns manually (requires render_cols="col1,col2,col3", 0=render columns dynamically
                render_cols=0, // columns rendered (only used when dt_ajax=1)
                edit=1, // add a column with a edit icon
                link_url="/ui/jobs/manage", // link of the icon if the edit attribute is set
                auto_id=1, // reads id from data and appends it to the link url
                index=0, // index from array to attach to the link
                colname="Investigate" // column name
            )
        });
      </script>
    </body>
  </html> */
function draw_datatable(selector,url=0,data=0,hiddencols=[],dt_ajax=1,render_cols=0,edit=0,link_url="/",auto_id=0,index=0,colname="View") { // var hiddencols = [{"targets":[1],"visible":false},{"targets":[2],"visible":false}]
    var temp_url = link_url;
    var dt_json = {
        "scrollX": "200px",
        "dom": 'frtipB',
        "order": [[ 0, "desc" ]], // "dom": 'Bfrtip',
        "buttons": [
            'csvHtml5',
            //'colvis',
        ],
        "columnDefs":[
          {'targets': 0,'width': "5%"}
        ]
    };
    // visible columns
    var arrayLength = hiddencols.length;
    for (var i = 0; i < arrayLength; i++) {
        dt_json["columnDefs"].push(hiddencols[i])
    }
    var edit_json = { // Icon for Actions
         'targets': -1,
         'searchable': false,
         'orderable': false,
         'width': "10%",
         'data': null,
         'render': function (data, type, row, meta){
               if (auto_id) {
                   var re_url = temp_url+"/"+encodeURIComponent(data[index]);
               }
               else {
                   var re_url = temp_url;
               };
               return "<td class='text-right'><a href="+re_url+"><svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='feather feather-search' style='color:#355480'><circle cx='11' cy='11' r='8'></circle><line x1='21' y1='21' x2='16.65' y2='16.65'></line></svg></a></td>"
               //return "<td class='text-right'><a href="+re_url+"></a></td>"
         }
    };
    // Data source
    if (url) {
        dt_json["ajax"] = {"url":url} // ajax
        // Render column names
        if (render_cols) {
            var col = render_cols.split(",");
            $.each(col,function(i){
                $(selector+">thead>tr").append('<th>'+col[i]+'</th>');
            });
        };
    } else {
        dt_json["data"] = data["data"] // raw data
    }
    // Append Edit button
    if (edit) {
        $(selector+">thead>tr").append("<th>"+colname+"</th>");
        dt_json["columnDefs"].push(edit_json);
    };

    //dt_json["rowCallback"] = function(row,data,index) {
        //console.log(dataTable.column(index).header())
    //}

    // Draw table
    var table = $(selector).DataTable(dt_json);
    // Example script to toggle checkmarks
    //$(document).on('click', '.dropdown-item', function(event) {
    //    event.preventDefault();
    //    var toggle = table.column(this.id).visible();
    //    table.column(this.id).visible(!toggle);
    //    $(this).toggleClass('dropdown-item-checked');
    //});
    return table
}
function dt_init(selector,url,dt_ajax=1,render_cols=0,edit=0,link_url="/",auto_id=0,index=0,colname="View") {
    if (dt_ajax) {
        draw_datatable(selector,url=url,data=0,hiddencols=[],dt_ajax=1,render_cols=render_cols,edit=edit,link_url=link_url,auto_id=auto_id,index=index,colname=colname)
    } else {
        $.ajax({
             type: "GET",
             url: url,
             contentType: 'application/json',
             success: function(result) {
                 // Create columns for table based on data["columns"]
                 var columns = result["columns"];
                 $.each(columns,function(i) {
                     $(selector+">thead>tr").append('<th>'+columns[i]+'</th>');
                     //$(".dropdown-menu").append('<a id='+i+' href="#" class="dropdown-item dropdown-item-checked">'+columns[i]+'</a>');
                 });
                 draw_datatable(selector,url=0,data=result,hiddencols=result["hide"],dt_ajax=0,render_cols=0,edit=edit,link_url=link_url,auto_id=auto_id,index=index,colname=colname)
             },
             error: function(result) {console.log(result);}
        });
    }
}
function ajax_method(url,method="POST",data={}) {
  $.ajax({
         type: method,
         url: url,
         data: data,
         contentType: 'application/json',
         success: function(result) {
            notify_call(result["message"],result["type"]);
         },
         error: function(result) {
            notify_call("Error","danger");
         }
   });
}
function notify_call(message,type) {
    $.notify({
      // options
      message: message
    },{
      // settings
      type: type
    });
}
