var application = function(){

  var serviceName = 'PepperSurvey'
  var self = this;

  var displayContainer = $('#question-choices-container')
  var progressBarIndicator = $('#progress-bar .indicator')

  function sendEvent(event, value) {
      console.log("sendEvent => " + event + ":" + JSON.stringify(value));
      try{
        service.onTabletEvent(event, value);
      }catch(e){
        console.log("error on send event "+e)
      }
  }

  self.testEvent = function(event, value){
    onTabletEvent(event, value)
  } 

  function onTabletEvent(event, value){
    console.log('onTabletEvent => '+event+' : '+JSON.stringify(value));

    switch (event) {
      case "STATE_CHANGED":
        $('body').attr('class', value.toLowerCase())
        break;

      case "TOGGLE_NEXT_BUTTON":
        $('#question-next-button').toggleClass('activated', value);
        break;

      case "SET_QUESTION":
        // title
        $('#question-heading').html('<span>'+value.title+'</span>').textfill();

        // UI
        displayAnswerUI(value)
        
        // progress bar
        progressBarIndicator.css('width', value.progression+'%')
        break;

      case "SELECT_ANSWER":
        $('input[value="'+value+'"]').prop('checked', true).change()
        break;

    }
  }

  $('#question-next-button').on('click', function(e){
    sendEvent("ON_NEXT_QUESTION")
  })

  $('#button-quit').on('click', function(e){
    sendEvent('QUIT')
  })

  var displayAnswerUI = function(question){
      displayContainer.attr('class', question.type).html('')
      switch (question.type) {
        case "single_choice":
          displayList(question.answers.choices, 'radio')
          break;

        case "multiple_choice":
          displayList(question.answers.choices, 'checkbox')
          break;

        case "single_line":
          displayInput('input')
          break;

        case "multiple_line":
          displayInput('textarea')
          break;

        case "nps":
          displayNPS(question.answers)
          break;

        case "slider":
          displaySlider(question.display_options);
          break;

        case "rating":
        case "matrix":
          displayMatrix(question.answers, question.subtype, question.display_options)
          break;
      }
  }

  var displayInput = function(type){
    var input = $(document.createElement(type)).on('keyup', function(e){
      $(this).data('answer', {"text": $(this).val().replace(/\n/g, '\r')}).change()
      if($(this).is('input') && e.keyCode == 13) $(this).blur()
    }).on('focus', function(e){
      $('body').toggleClass('editing', true);
    }).on('blur', function(e){
      $('body').toggleClass('editing', false);
    }).on('change', {'selector': type}, onInputChanged).appendTo(displayContainer)
  }

  var hideTimeout = null;
  var displaySlider = function(options){

    var input_value = $(document.createElement('input')).attr({
      'type': 'text',
      'id': 'display_number'
    }).on('change', {'selector': '#display_number'}, onInputChanged)

    var indicator = $(document.createElement('div')).attr('class', 'indicator').append(input_value)

    var slider = $(document.createElement('input')).attr({
      'type': 'range',
      'step': options.custom_options.step_size,
    }).on('mousedown touchstart', function(e) {
      clearTimeout(hideTimeout)
      indicator.show()
    }).on('touchend mouseup', function(e){
      hideTimeout = setTimeout(function(){
        indicator.hide()
      }, 1000)
      input_value.data('answer', {"text": $(this).val()}).change();
    }).on('input', function(e){
      var value = $(this).val()
      indicator.css('left', value+'%');
      input_value.val(value)
    })

    var indicatorContainer = $(document.createElement('div')).attr('class', 'indicator-container').append(indicator)

    $(document.createElement('div')).attr('id', 'wrapper').append(
      $(document.createElement('div')).attr('id', 'left_label').html(options.left_label), 
      $(document.createElement('div')).attr('id', 'slider-container').append(slider, indicatorContainer), 
      $(document.createElement('div')).attr('id', 'right_label').html(options.right_label)
    ).appendTo(displayContainer)

    slider.val(options.custom_options.starting_position)
  }

  var displayList = function(choices, type){
    var ul = $(document.createElement('ul'))
    $.each(choices, function(index, el) {
      var input = $(document.createElement('input')).attr({
        'value': el.id,
        'name': 'choice_id',
        'type': type,
        'id': el.id
      }).data('answer', {
        'choice_id': el.id
      }).on('change', {'selector': 'input:checked'}, onInputChanged);
      var label = $(document.createElement('label')).attr({'for': el.id}).html(el.text);
      ul.append($(document.createElement('li')).append(input, label))
    });

    $(document.createElement('div')).attr('class', 'wrapper').append(ul).appendTo(displayContainer);
  }

  var displayMatrix = function(answers, subtype, display_options){
    var table = $(document.createElement('table')).attr({'class': subtype})
    var header = $(document.createElement('tr'))
    if(answers.rows.length > 1) header.append('<th />')
    $.each(answers.choices, function(idx, e){
        $(document.createElement('th')).html(e.text).appendTo(header)
    })
    table.append(header)

    $.each(answers.rows, function(index, row){
      var r = $(document.createElement('tr'))
      if(answers.rows.length > 1) r.append('<td>'+row.text+'</td>')
      var _group_name = 'choice_id-'+index
      $.each(answers.choices, function(idx, e){
        var _id = row.id+'_'+e.id;
        var input = $(document.createElement('input')).attr({
          'type': 'radio',
          'value': e.id,
          'name':_group_name,
          'id': _id
        }).data('answer', {
          "row_id": row.id,
          "choice_id": e.id
        }).on('change', {'selector': 'input:checked'}, onInputChanged);
        var label = $(document.createElement('label')).attr({'for': _id});
        $(document.createElement('td')).append(input, label).appendTo(r);
      })
      table.append(r)
    })

    if(display_options){

      table.addClass(display_options.display_type+' '+display_options.display_subtype)
      .css('color', display_options.custom_options.color);

      if(display_options.show_display_number){
        $('input[type=radio]', table).on('change', function(e){
          var cl = 'selected'
          $('input[type=radio]', table).each(function(index, elt){
            $(this).attr('class', cl)
            if( $(this).attr('id') == $(e.currentTarget).attr('id')) cl = ''
          })
        })
      }
    }

    table.appendTo(displayContainer)
  }

  var displayNPS = function(answers){
    var table = $(document.createElement('table')).attr({'class': 'nps'})

    var row_id = answers.rows[0].id;

    var tr = $(document.createElement('tr'));

    $.each(answers.choices, function(idx, e){
      var td = $(document.createElement('td'))
      var _id = row_id+'_'+e.id;
      var input = $(document.createElement('input')).attr({
          'type': 'radio',
          'value': e.id,
          'name': 'nps',
          'id': _id
        }).data('answer', {
          "row_id": row_id,
          "choice_id": e.id
        }).on('change', {'selector': 'input:checked'}, onInputChanged);
        var label = $(document.createElement('label')).attr({'for': _id}).html(idx);

        td.append(input, label).appendTo(tr)
    })

    table.append(tr).appendTo(displayContainer)
  }

  var onInputChanged = function(e){
    answers = []
    $('#question-choices-container '+e.data.selector).each(function(index, el) {
      answers.push($.data(this, 'answer'))
    });
    sendEvent('ON_ANSWER_CHANGED', answers)
  }

  var service = null;
  function onConnected(session){
    console.log('connected');
    session.service(serviceName).then(function (serv) {
      service = serv;
      service.tabletEvent.connect(onTabletEvent).then(function(){
        sendEvent('LOADED', 'true');
      })
    })
  }

  function onDisconnected(err){
    console.log('disconneted : '+ error);
  }

  RobotUtils.connect(onConnected, onDisconnected);

  return self;
}
