from flask import Flask, send_file

app = Flask(__name__)

@app.route('/wiitv')
def wiitv():
    return send_file('swf/leanbacklite_wii.swf', mimetype='application/x-shockwave-flash')
    
@app.route('/player_204')
def player_204():
    return ('')

@app.route('/leanback_ajax')
def leanbackajax():
   return send_file('leanback_ajax')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
