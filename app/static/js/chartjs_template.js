/*
Description: Quickly render chartjs graphs
Usage:
  <html>
    <body>
      <div class="row">
        <div class="col-lg-6">
          <div class="card card-chart">
            <div class="card-header">
              <h1 class="card-category">Card Header</h1>
              <h3 class="card-title"><i class="tim-icons icon-bulb-63 text-success"></i>Sub Header</h3>
            </div>
            <div class="card-body">
              <div class="chart-area">
                <canvas id="chart1"></canvas>
              </div>
            </div>
          </div>
        </div>
      </div>
      <script>
        $(document).ready(function (){
            $.noConflict();

            // draw chartjs
            var table2 = cjs_init(
                selector="chart1",
                url="/api/agent/data/users?as_chartjs=true&groupby=email,count",
                type="bubble", // type of graph (line,pie,bar,doughnut,polarArea)
                graph_label="Testing", // header of graph
            );
        });
      </script>
    </body>
  </html>
*/

function draw_chartjs(selector,type,labels,values,graph_label="Graph",xticks=true,yticks=true,header=true,funcolors) {
  var obj = {
    "type":type,
    "data":{
        "labels": labels,
        "datasets": [
          {
            "label": graph_label,
            "borderColor": "white",
            "borderWidth": 1,
            "data": values,
//            "backgroundColor": Chart['colorschemes'].tableau.ClassicMedium10,
          }
        ]
    },
    "options": {
      "scales":{
        "xAxes":[{"ticks":{"fontColor":"white","beginAtZero": true}},{"gridLines": {"drawOnChartArea":false}}],
        "yAxes":[{"ticks":{"fontColor":"white","beginAtZero": true}},{"gridLines": {"drawOnChartArea":false}}],
      },
      "responsive":true,
      "maintainAspectRatio": false,
      "animation": {
        "duration": 3000
      },
      "legend": {
        //"display":false, // disable header label
        "labels": {
          "fontColor":"white"
        }
      },
      "plugins": {
        "colorschemes": {
          "scheme": 'tableau.ClassicMedium10'
        }
      }
    }
  };
  if (!xticks || type=="doughnut") {
//      obj.options = {"scales":{"xAxes":[{"ticks":{"display":false}}]}};
      obj.options.scales.xAxes = [{"ticks":{"display":false}}];
  };
  if (!yticks || type=="doughnut") {
//      obj.options = {"scales":{"xAxes":[{"ticks":{"display":false}}]}};
      obj.options.scales.yAxes = [{"ticks":{"display":false}}];
  };
  if (!header) {
    obj["options"]["legend"]["display"] = false;
  }
  if (funcolors) {
    obj["data"]["datasets"][0]["backgroundColor"] = Chart['colorschemes'].tableau.ClassicMedium10
  }
  new Chart(document.getElementById(selector), obj);
};

function cjs_init(selector,url,type,graph_label,xticks=true,yticks=true,header=true,funcolors=false) {
    $.ajax({
        type: "GET",
        url: url,
        contentType: 'application/json',
        success: function(result) {
            draw_chartjs(selector,type,result["label"],result["data"],graph_label,xticks,yticks,header,funcolors);
        },
        error: function(result) {console.log(result);}
    });
}
