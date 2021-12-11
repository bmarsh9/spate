function resetSidebar() {
  $("#tabs-trigger").html("")
  $("#tabs-action").html("")
  $("#tabs-misc").html("")
}

function fillSidebar(response) {
    $.each(response, function (index, value) {
      if (value["type"] === "trigger") {
        $("#tabs-trigger").append(value["html"]);
      } else if (value["type"] === "action") {
        $("#tabs-action").append(value["html"]);
      } else if (value["type"] === "misc") {
        $("#tabs-misc").append(value["html"]);
      }
    });
}

$(window).on('load', function() {
  let timeoutID = null;

  var $flowchart = $("#example");
  var $container = $flowchart.parent();

  function findMember(str) {
      $.ajax({
        url: "/api/v1/workflows/"+get_workflow_id()+"/sidebar?search="+str,
        type: "GET",
        contentType: "application/json; charset=utf-8",
        success: function (response) {
          resetSidebar()
          fillSidebar(response)
          initSidebar($flowchart,$container)
        },
        error: function (request, status, error) {
          notify_js("Error occurred while searching", type = "warning",time=1000)
        }
      });
  }
  $('#target').keyup(function(e) {
    clearTimeout(timeoutID);
    const value = e.target.value
    timeoutID = setTimeout(() => findMember(value), 500)
  });
});

function get_workflow_id() {
  return $("#workflow_id").attr("value")
};

// Events
$(document).on('click','.workflow_endpoints', function(){
  $("#workflow-endpoints").modal("show");
});
$(document).on('click','.workflow_form_endpoints', function(){
  $("#workflow-form-endpoints").modal("show");
});
$(document).on('click','.workflow_refresh', function(){
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/actions/refresh",
    type: "GET",
    success: function (response) {
        $("#refresh_button").html('<button class="btn workflow_refresh"><i class="ti ti-checks text-green"></i><small class="ml-2">Refresh</small></button>')
        notify_js("Refreshed workflow", type = "primary",time=1000)
    },
    error: function (request, status, error) {
        $("#refresh_button").html('<button class="btn workflow_refresh"><span style="width:1rem;height:1rem" class="spinner-grow text-orange" role="status"></span><small class="ml-2">Refresh</small></button>')
        notify_js("Error occurred", type = "warning",time=1000)
    }
  });
});
$(document).on('click','.workflow_run', function(){
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/actions/run",
    type: "GET",
    success: function (response) {
      console.log(response)
      $("#workflow-run").html(response["results"])
      $(".modal-title").html("Workflow Results")
      $("#workflow-modal-run").modal("show");
    },
    error: function (request, status, error) {
      notify_js("Error occurred", type = "warning",time=1000)
    }
  });
});
$(document).on('click','.workflow_settings', function(){
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/config",
    type: "GET",
    success: function (response) {
      $("#workflow-settings").html(response["config"])
      $(".modal-title").html("Workflow Settings")
      $("#workflow-modal").modal("show");
    },
    error: function (request, status, error) {
        notify_js("Error occurred", type = "warning",time=1000)
    }
  });
});
function saveWorkflowSettings(name) {
  if ($("#workflow_enabled").is(":checked")) {
    var enabled = true;
  } else {
    var enabled = false;
  };
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/config",
    type: "PUT",
    data: JSON.stringify({
      "label":$("#workflow_label").val(),
      "description":$("#workflow_description").val(),
      "enabled":enabled,
      "imports":$("#workflow_imports").val(),
      "log_level":$("#log_level").val(),
    }),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function (response) {
      $("#workflow-modal").modal("toggle");
      notify_js("Saved settings", type = "primary",time=1000)
      return true;
    },
    error: function (request, status, error) {
      $("#workflow-modal").modal("toggle");
      notify_js("Unknown error", type = "warning",time=1000)
      return false;
    }
  });
}
// end events

function splitOnUnderScore(value) {
  if (value.includes("_")) {
    return value.split("_")[1]
  } else {
    return value
  }
}

function resetModalCodeArea() {
  $("#code-editor-wrapper").empty();
  $("#code-editor-wrapper").html('<div id="code-editor"></div>');
}

function resetInputColors() {
  $(".inputCodeIcon").addClass("text-secondary")
  $(".inputSettingsIcon").addClass("text-secondary")
  $(".inputHeader").addClass("text-secondary")
  $(".modalInputSidebar").css("background-color","white")
  $("#operatorHeaderInputs").css("border-top","3px solid #e6e8e9")
  $(".card-progress").remove()
}

function resetOutputColors() {
  $(".outputCodeIcon").addClass("text-secondary")
  $(".outputSettingsIcon").addClass("text-secondary")
  $(".outputHeader").addClass("text-secondary")
  $(".modalOutputSidebar").css("background-color","white")
  $("#operatorHeaderOutputs").css("border-top","3px solid #e6e8e9")
  $(".card-progress").remove()
}

function resetOperatorButtonColor() {
  $(".modalOperatorButton").removeClass("btn-primary")
  $(".modalOperatorButton").html("Show Operator Logic")
  $("#operatorHeaderLogic").css("border-top","3px solid #e6e8e9")
  $(".card-progress").remove()
}

function resetModalColors() {
  resetInputColors()
  resetOutputColors()
  resetOperatorButtonColor()
}

function selectInput(name,icon) {
  $("#"+name+"_input").css('background-color', '#e6e8e9')
  if (icon === "code") {
    $("#"+name+"_inputCodeIcon").removeClass("text-secondary")
    $("#modalSaveButton").html('<button onclick=saveInputCode("'+name+'") type="button" class="btn subheader text-white btn-primary">Save</button>')
  } else {
    $("#"+name+"_inputSettingsIcon").removeClass("text-secondary")
    $("#modalSaveButton").html('<button onclick=saveInputSettings("'+name+'") type="button" class="btn subheader text-white btn-primary">Save</button>')
  }
  $("#"+name+"_inputHeader").removeClass("text-secondary")
  $("#operatorHeaderInputs").css("border-top","3px solid #206bc4")
  var progress_bar = '<div class="progress progress-sm card-progress progress-bar-indeterminate"><div class="progress-bar" style="width: 50%" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"><span class="visually-hidden">100% Complete</span></div></div>';
  $("#"+name+"_input").after(progress_bar)
}

function selectOutput(name,icon) {
  //$("#"+name+"_link").css('background-color', '#e6e8e9')
  if (icon === "code") {
    $("#"+name+"_linkCodeIcon").removeClass("text-secondary")
    $("#modalSaveButton").html('<button onclick=saveLinkCode("'+name+'") type="button" class="btn subheader text-white btn-primary">Save</button>')
  } else {
    $("#"+name+"_linkSettingsIcon").removeClass("text-secondary")
    $("#modalSaveButton").html('<button onclick=saveLinkSettings("'+name+'") type="button" class="btn subheader text-white btn-primary">Save</button>')
  }
  $("#"+name+"_linkHeader").removeClass("text-secondary")
  $("#operatorHeaderOutputs").css("border-top","3px solid #206bc4")
  var progress_bar = '<div class="progress progress-sm card-progress progress-bar-indeterminate"><div class="progress-bar" style="width: 50%" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"><span class="visually-hidden">100% Complete</span></div></div>';
  $("#"+name+"_link").after(progress_bar)
}

function clickOperatorInputCode(name) {
  resetModalColors()
  selectInput(name,"code")
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/inputs/" + name + "/code",
    type: "GET",
    success: function (response) {
      resetModalCodeArea()
      var editor = ace.edit("code-editor");
      editor.setOptions({
        maxLines: 50,
        minLines: 50,
        autoScrollEditorIntoView: true,
      });
      editor.setTheme("ace/theme/monokai");
      editor.session.setMode("ace/mode/python");
      editor.session.setTabSize(4);
      editor.session.setUseWrapMode(true);
      editor.setValue(response["code"]);
      readOnlyLines(editor);
    }
  });
}

function clickOperatorInputSettings(name) {
  resetModalColors()
  selectInput(name,"settings")
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/inputs/" + name + "/config",
    type: "GET",
    success: function (response) {
      resetModalCodeArea()
      $("#code-editor").html(response["config"])
    }
  });
}

function clickLinkOutputCode(name) {
  resetModalColors()
  selectOutput(name,"code")
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/links/" + name + "/code",
    type: "GET",
    success: function (response) {
      var editor = ace.edit("code-editor");
      editor.setOptions({
        maxLines: 50,
        minLines: 50,
        autoScrollEditorIntoView: true,
      });
      editor.setTheme("ace/theme/monokai");
      editor.session.setMode("ace/mode/python");
      editor.session.setTabSize(4);
      editor.session.setUseWrapMode(true);
      editor.setValue(response["code"]);
      readOnlyLines(editor);
    }
  });
}

function clickLinkOutputSettings(name) {
  resetModalColors()
  selectOutput(name,"settings")
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/links/" + name + "/config",
    type: "GET",
    success: function (response) {
      resetModalCodeArea()
      $("#code-editor").html(response["config"])
    }
  });
}

function clickOperatorSettings(operatorName) {
  resetModalColors()
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/operators/" + operatorName + "/config",
    type: "GET",
    success: function (response) {
      resetModalCodeArea()
      $("#code-editor").html(response["config"])
      $("#modalSaveButton").html('<button onclick=saveOperatorSettings("'+operatorName+'") type="button" class="btn subheader text-white btn-primary">Save</button>')
    }
  });
}

$('#operator-modal').on('hide.bs.modal', function () {
  var editor = ace.edit("code-editor");
  editor.setValue();
})

function saveOperatorCode(operatorName) {
  var editor = ace.edit("code-editor");
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/operators/"+operatorName+"/code",
    type: "PUT",
    data: JSON.stringify({
      "code":editor.getValue(),
    }),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function (response) {
      notify_js("Saved successfully",type="primary")
      return true;
    },
    error: function (request, status, error) {
      notify_js("Hmm. Something went wrong. Your data may not have saved!", type="danger")
      return false;
    }
  });
}

function saveOperatorSettings(operatorName) {
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/operators/"+operatorName+"/config",
    type: "PUT",
    data: JSON.stringify({
      "label":$("#label_"+operatorName).val(),
      "description":$("#description_"+operatorName).val(),
      "enabled":$("#enabled_"+operatorName).is(":checked"),
      "imports":$("#imports_"+operatorName).val(),
      "return_path":$("#path_"+operatorName+" input[type='radio']:checked").val(),
      "synchronous":$("#synchronous_"+operatorName).val(),
      "runevery":$("#runevery_"+operatorName).val(),
      "form":$("#form_"+operatorName).val(),
    }),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function (response) {
      notify_js("Saved successfully",type="primary")
      return true;
    },
    error: function (request, status, error) {
      notify_js("Hmm. Something went wrong. Your data may not have saved!", type="danger")
      return false;
    }
  });
}

function saveLinkCode(linkName) {
  var editor = ace.edit("code-editor");
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/links/"+linkName+"/code",
    type: "PUT",
    data: JSON.stringify({
      "code":editor.getValue(),
    }),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function (response) {
      notify_js("Saved successfully",type="primary")
      return true;
    },
    error: function (request, status, error) {
      notify_js("Hmm. Something went wrong. Your data may not have saved!", type="danger")
      return false;
    }
  });
}

function saveLinkSettings(linkName) {
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/links/"+linkName+"/config",
    type: "PUT",
    data: JSON.stringify({
      "label":$("#label_"+linkName).val(),
      "description":$("#description_"+linkName).val(),
      "enabled":$("#enabled_"+linkName).is(":checked"),
      "imports":$("#imports_"+linkName).val(),
    }),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function (response) {
      notify_js("Saved successfully",type="primary")
      return true;
    },
    error: function (request, status, error) {
      notify_js("Hmm. Something went wrong. Your data may not have saved!", type="danger")
      return false;
    }
  });
}

function loadOperatorModal(operatorName) {
  resetModalColors()
  loadEditor(operatorName)
  loadInputs(operatorName)
  loadOutputs(operatorName)
}

function loadInputs(operatorName) {
  $.ajax({
    url: "/api/v1/operators/" + operatorName + "/inputs",
    type: "GET",
    success: function (response) {
      $("#operatorInputs").html(response)
    },
    error: function (request, status, error) {
      console.log("error")
      return false;
    }
  });
}
function loadOutputs(operatorName) {
  $.ajax({
    url: "/api/v1/operators/" + operatorName + "/outputs",
    type: "GET",
    success: function (response) {
      $("#operatorOutputs").html(response)
    },
    error: function (request, status, error) {
      console.log("error")
      return false;
    }
  });
}

function readOnlyLines(editor) {
  editor.commands.on("exec", function(e) {
    var rowCol = editor.selection.getCursor();
    var last_3 = editor.session.getLength() - 5
    if (rowCol.row < 3 || rowCol.row > last_3) {
      editor.gotoLine(3);
      editor.navigateLineEnd()
      if (e.args === "\n") {
        console.log("new line")
      } else {
        e.preventDefault();
        e.stopPropagation();
      }
    }
  });
}

function loadEditor(operatorName) {
  resetModalColors()
  $("#operatorButtonView").html('<a href="#" onclick=loadEditor("'+operatorName+'") class="btn btn-sm btn-primary mr-2 modalOperatorButton">Reload Logic<i class="ti ti-refresh ml-2"></i></a><a href="#" onclick=clickOperatorSettings("'+operatorName+'") class="btn btn-sm bg-yellow-lt">Settings<i class="ti ti-tools ml-2"></i></a>');
  $("#operatorHeaderLogic").css("border-top","3px solid #206bc4")
  // load code editor
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/operators/" + operatorName + "/code",
    type: "GET",
    success: function (response) {
      var editor = ace.edit("code-editor");
      editor.setOptions({
        maxLines: 50,
        minLines: 50,
        autoScrollEditorIntoView: true,
      });
      editor.setTheme("ace/theme/monokai");
      editor.session.setMode("ace/mode/python");
      editor.session.setTabSize(4);
      editor.session.setUseWrapMode(true);
      //editor.setReadOnly(true);  // false to make it editable
      editor.setValue(response["code"]);
      readOnlyLines(editor);
      /*
      editor.getSession().setAnnotations([{
        row: 1,
        column: 0,
        text: "Error Message", // Or the Json reply from the parser 
        type: "error" // also "warning" and "information"
      }]);
      */
    },
    error: function (request, status, error) {
      console.log("error")
      return false;
    }
  });
  $("#modalSaveButton").html('<button onclick=saveOperatorCode("'+operatorName+'") type="button" class="btn subheader text-white btn-primary">Save</button>')
}

function showEvent(txt) {
  console.log(txt)
}

function loadFlowchart(selector, workflowId) {

  // clear the flowchart
  $("#chart_container").html('<div class="flowchart-example-container" id="example"></div>')

  var $flowchart = $(selector);
  var $container = $flowchart.parent();

  var cx = $flowchart.width() / 2;
  var cy = $flowchart.height() / 2;

  // Panzoom initialization...
  $flowchart.panzoom();

  $("#reset_zoom").on("click", function () {
    $flowchart.panzoom('pan', -cx + $container.width() / 2, -cy + $container.height() / 2);
  })

  // Centering panzoom
  $flowchart.panzoom('pan', -cx + $container.width() / 2, -cy + $container.height() / 2);

  function setInitialZoom() {
    $flowchart.flowchart('setPositionRatio', .8);
    $flowchart.panzoom('zoom', .8, {
      animate: true,
    });
  }

  // initialize events
  $(document).on('click','.delete_operator', function(){
    $flowchart.flowchart('deleteOperator', $(this).attr("id"));
  })
  $(document).on('click','.edit_operator', function(){
    $("#operator-modal").modal("show");
    var operatorName = $(this).attr("id");
    $.ajax({
      url: "/api/v1/workflows/"+get_workflow_id()+"/operators/" + operatorName + "/meta",
        type: "GET",
        success: function (response) {
          $(".modal-title").html(response["label"])
          loadOperatorModal(operatorName)
        },
        error: function (request, status, error) {
          notify_js("Error occurred", type = "warning",time=1000)
        }
    });
  });
  $('#operator-modal').on('hide.bs.modal', function () {
    var editor = ace.edit("code-editor");
    editor.setValue("")
  })
  /*
  $('#operator-modal').on('shown.bs.modal', function () {
  });
  */

  // Panzoom zoom handling...
  /*
  var possibleZooms = [0.5, 0.75, 1, 2, 3];
  var currentZoom = 0.5;
  $container.on('mousewheel.focal', function(e) {
    e.preventDefault();
    var delta = (e.delta || e.originalEvent.wheelDelta) || e.originalEvent.detail;
    var zoomOut = delta ? delta < 0 : e.originalEvent.deltaY > 0;
    currentZoom = Math.max(0, Math.min(possibleZooms.length - 1, (currentZoom + (zoomOut * 2 - 1))));
    $flowchart.flowchart('setPositionRatio', possibleZooms[currentZoom]);
    $flowchart.panzoom('zoom', possibleZooms[currentZoom], {
      animate: true,
      focal: e
    });
  });
  */
  //}


  // Apply the plugin on a standard, empty div...
  //function loadWorkflow(workflowId) {

  //make ajax call for data
  $.ajax({
    url: "/api/v1/workflows/" + workflowId,
    type: "GET",
    success: function (response) {
      $flowchart.flowchart({
        data: response,
        linkWidth: 5,
        multipleLinksOnOutput: true,
        multipleLinksOnInput: true,
        onOperatorSelect: function (operatorId) {
          return true;
        },
        onOperatorUnselect: function () {
          showEvent('Operator unselected.');
          return true;
        },
        onLinkSelect: function (linkId) {
          showEvent('Link "' + linkId + '" selected. Main color: ' + $flowchart.flowchart('getLinkMainColor', linkId) + '.');
          return true;
        },
        onLinkUnselect: function () {
          showEvent('Link unselected.');
          return true;
        },
        onOperatorCreate: function (operatorId, operatorData, fullElement) {
          //showEvent('New operator created. Operator ID: "' + operatorId + '", operator title: "' + operatorData.properties.title + '".');
          return true;
        },
        onLinkCreate: function (linkId, linkData) {
          if (linkId in response["links"]) {
              // on initial load of the workflow, this callback will fire.
              // this will check if the linkId is already created/loaded from
              // the first initial load
              return true;
          };
          //if (linkId in $flowchart.flowchart('getData')["links"]) {
          //    console.log("skipping link creation")
          //}
          if (typeof linkId === 'string' || linkId instanceof String) {
            // check if created link is a string, which means it was already
            // created on the server
            return true;
          }
          if (!linkData.fromConnector) {
              return true;
          }
          $.ajax({
            url: "/api/v1/workflows/"+get_workflow_id()+"/links",
            type: "POST",
            data: JSON.stringify({
              "from_operator":linkData.fromOperator,
              "from_connector":linkData.fromConnector,
              "to_operator":linkData.toOperator,
              "to_connector":linkData.toConnector,
            }),
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            success: function (response) {
              notify_js("Added Link", type = "primary",time=1000)
              $flowchart.flowchart('createLink', response["link_id"], response["link_data"]);
              var currentData = $flowchart.flowchart('getData');
              $flowchart.flowchart('setData', currentData);
              $flowchart.flowchart('redrawLinksLayer')
              return false;
            },
            error: function (request, status, error) {
              notify_js("Failed to add Link", type = "danger",time=1000)
              return false;
            }

          });
          return false;
        },
        onOperatorDelete: function (operatorId) {
          $.ajax({
            url: "/api/v1/workflows/"+get_workflow_id()+"/operators/" + operatorId,
            type: "DELETE",
            success: function (response) {
              notify_js("Deleted block", type = "warning",time=1000)
              var data = $flowchart.flowchart('getData');
              $flowchart.flowchart('setData', data);
            },
            error: function (request, status, error) {
              notify_js("Error occurred", type = "warning",time=1000)
            }
          });
          return true;
        },
        onLinkDelete: function (linkId, forced) {
          if (forced) {
              return false;
          };
          $.ajax({
            url: "/api/v1/workflows/"+get_workflow_id()+"/links/"+linkId,
            type: "DELETE",
            success: function (response) {
              notify_js("Deleted Link", type = "primary",time=1000)
            },
            error: function (request, status, error) {
              notify_js("Error occurred", type = "warning",time=1000)
            }
          });
          return true;
        },
        onOperatorMoved: function (operatorId, position) {
          $.ajax({
            url: "/api/v1/workflows/"+get_workflow_id()+"/operators/"+operatorId+"/position",
            type: "PUT",
            data: JSON.stringify({
              "top":position.top,
              "left":position.left,
            }),
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            success: function (response) {
              console.log("operator moved")
            },
            error: function (request, status, error) {
              notify_js("Error occurred", type = "warning",time=1000)
            }
          });
        },
        onAfterChange: function (operatorEvent) {
          //pass
        }
      });
      setInitialZoom()
    }, //end ajax success callback
    error: function (request, status, error) {
      notify_js("Failed to load the flowchart!", type = "danger",time=1000)
      return false;
    }
  }); // end ajax get load workflow data

  $flowchart.parent().siblings('.delete_selected_button').click(function () {
    $flowchart.flowchart('deleteSelected');
  });

  $("#delete_selected_button").click(function () {
    $flowchart.flowchart('deleteSelected');
  })

  $("#get_data").click(function () {
    var data = $flowchart.flowchart('getData');
    $('#flowchart_data').val(JSON.stringify(data, null, 2));
    console.log(data)
    notify_js("Check console for debugging", type = "primary",time=1000)
  })
  /*
  $("#set_data").click(function () {
    var data = $flowchart.flowchart('getData');
    $.ajax({
      url: "/api/v1/workflows/"+get_workflow_id()+"/config",
      type: "PUT",
      data: JSON.stringify(data, null, 2),
      contentType: "application/json; charset=utf-8",
      dataType: "json",
      success: function (data) {
        notify_js("Saved workflow", type = "primary",time=1000)
        var currentData = $flowchart.flowchart('getData');
        $flowchart.flowchart('setData', currentData);
      },
      error: function (request, status, error) {
        notify_js("Error occurred", type = "warning",time=1000)
      }
    });
  })
  */

  // Get sidebar
  $.ajax({
    url: "/api/v1/workflows/"+get_workflow_id()+"/sidebar",
    type: "GET",
    success: function (response) {
      resetSidebar()
      fillSidebar(response)
      initSidebar($flowchart,$container)
    }
  });
}; //end loadFlowchart function

function initSidebar($flowchart,$container) {
  var $draggableOperators = $('.draggable_operator');

  function getOperatorData($element) {
    var nbInputs = parseInt($element.data('nb-inputs'));
    var nbOutputs = parseInt($element.data('nb-outputs'));
    var data = {
      properties: {
        title: $element.text(),
        inputs: {},
        outputs: {},
        operator_id: $element.attr('id')
      }
    };

    var i = 0;
    for (i = 0; i < nbInputs; i++) {
      data.properties.inputs['input_' + i] = {
        label: 'Input ' + (i + 1)
      };
    }
    for (i = 0; i < nbOutputs; i++) {
      data.properties.outputs['output_' + i] = {
        label: 'Output ' + (i + 1)
      };
    }

    return data;
  }

  var operatorId = 0;

  $draggableOperators.draggable({
    cursor: "move",
    opacity: 0.7,

    helper: 'clone',
    appendTo: 'body',
    zIndex: 1000,

    helper: function (e) {
      var $this = $(this);
      var data = getOperatorData($this);
      return $flowchart.flowchart('getOperatorElement', data);
    },
    stop: function (e, ui) {
      var $this = $(this);
      var elOffset = ui.offset;
      var containerOffset = $container.offset();
      if (elOffset.left > containerOffset.left &&
        elOffset.top > containerOffset.top &&
        elOffset.left < containerOffset.left + $container.width() &&
        elOffset.top < containerOffset.top + $container.height()) {

        var flowchartOffset = $flowchart.offset();

        var relativeLeft = elOffset.left - flowchartOffset.left;
        var relativeTop = elOffset.top - flowchartOffset.top;

        var positionRatio = $flowchart.flowchart('getPositionRatio');
        relativeLeft /= positionRatio;
        relativeTop /= positionRatio;

        var data = getOperatorData($this);
        data.left = relativeLeft;
        data.top = relativeTop;

        //$flowchart.flowchart('addOperator', data);
        $.ajax({
          url: "/api/v1/workflows/"+get_workflow_id()+"/operators",
          type: "POST",
          data: JSON.stringify({"operator_id":splitOnUnderScore(data.properties.operator_id),
              "top":data.top,"left":data.left}),
          contentType: "application/json; charset=utf-8",
          dataType: "json",
          success: function (response) {
            notify_js("Added block", type = "primary",time=1000)
            var newData = {
              "top": data.top,
              "left": data.left,
              "properties": response["properties"]
            }
            $flowchart.flowchart('createOperator', response["operator_id"], newData);
            var currentData = $flowchart.flowchart('getData');

            //currentData["operators"][response["operator_id"]] = newData
            $flowchart.flowchart('setData', currentData);
            return false;
          },
          error: function (request, status, error) {
            notify_js("[WARNING] "+request.responseJSON["message"], type = "warning",time=1000)
            return false;
          }
        });

      }
    }
  });
}
